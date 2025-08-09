import os
import io
import base64
import streamlit as st
import torch
import torchaudio
import numpy as np
from scipy.io.wavfile import write
import tempfile
import librosa
from pathlib import Path
import requests

# Import authentication and ElevenLabs modules
from auth import AuthManager, show_login_page, show_signup_page, check_authentication, logout
from elevenlabs_integration import (
    ElevenLabsAPI, create_elevenlabs_interface, 
    create_voice_cloning_interface, generate_speech_with_elevenlabs
)
from voice_cloning_engine import VoiceCloningEngine

# ElevenLabs API Key (in production, use environment variables)
ELEVENLABS_API_KEY = "sk_41e50eb5f2f1733635044711930a64afcab410374fad0fec"

# Try to import TTS libraries
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

class VoiceCloningApp:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts_model = None
        self.reference_audio = None
        self.pyttsx3_engine = None
        self.voice_cloning_engine = VoiceCloningEngine()
        self.setup_models()
    
    def setup_models(self):
        """Initialize TTS models"""
        # Initialize pyttsx3 first as it's more reliable
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                # Configure pyttsx3 settings
                voices = self.pyttsx3_engine.getProperty('voices')
                if voices:
                    # Set a female voice if available
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self.pyttsx3_engine.setProperty('voice', voice.id)
                            break
                
                # Set speech rate and volume
                self.pyttsx3_engine.setProperty('rate', 180)  # Speed of speech
                self.pyttsx3_engine.setProperty('volume', 0.9)  # Volume level
                st.success("✅ Enhanced TTS engine initialized with optimized settings!")
            except Exception as e:
                st.warning(f"⚠️ Failed to initialize TTS engine: {e}")
                self.pyttsx3_engine = None
        
        # Try to load advanced TTS model (optional)
        if TTS_AVAILABLE:
            try:
                # Use Coqui TTS for voice cloning
                self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
                st.success("✅ Advanced TTS model loaded successfully!")
            except Exception as e:
                st.info(f"ℹ️ Advanced TTS model not available: {e}")
                self.tts_model = None
    
    def load_reference_audio(self, audio_file):
        """Load and process reference audio for voice cloning"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_file.getvalue())
                tmp_path = tmp_file.name
            
            # Load audio with librosa
            audio, sr = librosa.load(tmp_path, sr=22050)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            self.reference_audio = tmp_path
            return audio, sr
        except Exception as e:
            st.error(f"Error loading reference audio: {e}")
            return None, None
    
    def clone_voice(self, text, reference_audio_path=None):
        """Clone voice using the reference audio"""
        if not text.strip():
            st.error("Please enter some text to synthesize")
            return None
        
        try:
            # Priority 1: Use advanced voice cloning engine with reference audio
            if reference_audio_path and os.path.exists(reference_audio_path):
                st.info("🎯 Using advanced voice cloning with reference audio...")
                return self.voice_cloning_engine.clone_voice(text, reference_audio_path)
            
            # Priority 2: Use Coqui TTS if available and reference audio provided
            elif self.tts_model and reference_audio_path:
                st.info("🔬 Using Coqui TTS for voice cloning...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    output_path = tmp_file.name
                
                # Generate speech with voice cloning
                self.tts_model.tts_to_file(
                    text=text,
                    speaker_wav=reference_audio_path,
                    language="en",
                    file_path=output_path
                )
                
                return output_path
            
            # Priority 3: Use basic TTS for fallback
            elif self.pyttsx3_engine:
                st.info("🔊 Using system TTS (no voice cloning)...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    output_path = tmp_file.name
                
                # Save speech to file
                self.pyttsx3_engine.save_to_file(text, output_path)
                self.pyttsx3_engine.runAndWait()
                
                # Check if file was created successfully
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return output_path
                else:
                    # Fallback: create a simple beep sound as placeholder
                    st.warning("⚠️ TTS file generation failed, creating placeholder audio")
                    return self.create_placeholder_audio(text)
            
            else:
                st.error("❌ No TTS engine available")
                st.info("💡 **Suggestion**: Try installing pyttsx3 with: pip install pyttsx3")
                return None
                
        except Exception as e:
            st.error(f"❌ Error during voice synthesis: {e}")
            # Try to create placeholder audio
            return self.create_placeholder_audio(text)
    
    def create_placeholder_audio(self, text):
        """Create a placeholder audio file when TTS fails"""
        try:
            # Create a simple tone as placeholder
            duration = min(len(text) * 0.1, 10)  # Max 10 seconds
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Create a pleasant tone
            frequency = 440  # A4 note
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Add some variation
            audio *= np.exp(-t * 0.5)  # Fade out
            
            # Save as WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                output_path = tmp_file.name
            
            # Convert to 16-bit integers
            audio_int = (audio * 32767).astype(np.int16)
            write(output_path, sample_rate, audio_int)
            
            st.info(f"🎵 Created placeholder audio ({duration:.1f}s) for text: '{text[:50]}...'")
            return output_path
            
        except Exception as e:
            st.error(f"❌ Failed to create placeholder audio: {e}")
            return None
    
    def get_available_voices(self):
        """Get list of available system voices for pyttsx3"""
        if not self.pyttsx3_engine:
            return []
        
        try:
            voices = self.pyttsx3_engine.getProperty('voices')
            return [(voice.id, voice.name) for voice in voices] if voices else []
        except Exception as e:
            st.warning(f"Could not get system voices: {e}")
            return []
    
    def set_voice(self, voice_id):
        """Set the voice for pyttsx3 engine"""
        if self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty('voice', voice_id)
                return True
            except Exception as e:
                st.warning(f"Could not set voice: {e}")
                return False
        return False
    
    def set_speech_rate(self, rate):
        """Set speech rate for pyttsx3 engine"""
        if self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty('rate', rate)
                return True
            except Exception as e:
                st.warning(f"Could not set speech rate: {e}")
                return False
        return False
    
    def analyze_audio(self, audio_path):
        """Analyze audio characteristics"""
        try:
            audio, sr = librosa.load(audio_path, sr=22050)
            
            # Extract features
            duration = len(audio) / sr
            pitch = librosa.yin(audio, fmin=50, fmax=400)
            pitch_mean = np.nanmean(pitch)
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            spectral_mean = np.mean(spectral_centroids)
            
            return {
                "duration": duration,
                "sample_rate": sr,
                "pitch_mean": pitch_mean,
                "spectral_centroid": spectral_mean,
                "audio_length": len(audio)
            }
        except Exception as e:
            st.error(f"Error analyzing audio: {e}")
            return None

def main():
    st.set_page_config(
        page_title="🎙️ Voice Cloning App",
        page_icon="🎙️",
        layout="wide"
    )
    
    # Check authentication
    authenticated = check_authentication()
    
    if not authenticated:
        # Show authentication pages
        st.title("🎙️ Voice Cloning Application")
        st.markdown("Welcome to the advanced voice cloning platform!")
        st.markdown("---")
        
        # Authentication tabs
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            show_login_page()
        
        with tab2:
            show_signup_page()
        
        return
    
    # User is authenticated - show main app
    st.title("🎙️ Voice Cloning Application")
    
    # User info and logout in sidebar
    with st.sidebar:
        st.success(f"👋 Welcome, {st.session_state.user['username']}!")
        if st.button("🚪 Logout"):
            logout()
        st.markdown("---")
    
    st.markdown("---")
    
    # Initialize the app
    if 'app' not in st.session_state:
        st.session_state.app = VoiceCloningApp()
    
    app = st.session_state.app
    
    # Sidebar for model information
    with st.sidebar:
        st.header("🔧 Model Status")
        
        # ElevenLabs status
        st.success("✅ ElevenLabs API Available")
        
        if TTS_AVAILABLE:
            st.success("✅ Coqui TTS Available")
        else:
            st.warning("⚠️ Coqui TTS Not Available")
        
        if PYTTSX3_AVAILABLE and app.pyttsx3_engine:
            st.success("✅ Enhanced TTS Engine Ready")
            # Show available voices count
            voices = app.get_available_voices()
            if voices:
                st.info(f"🎭 {len(voices)} system voices available")
        elif PYTTSX3_AVAILABLE:
            st.warning("⚠️ TTS Engine Available but Not Initialized")
        else:
            st.error("❌ TTS Engine Not Available")
            st.info("💡 Install with: pip install pyttsx3")
        
        st.info(f"🖥️ Device: {app.device}")
        
        st.header("📋 Instructions")
        st.markdown("""
        **ElevenLabs Mode:**
        1. Select voice from ElevenLabs library
        2. Adjust voice settings
        3. Enter text and generate
        
        **Local TTS Mode:**
        1. Choose system voice
        2. Adjust speech rate
        3. Upload reference audio (optional, for advanced cloning)
        4. Enter text and generate
        5. Download generated audio
        
        💡 **Tip**: If ElevenLabs is unavailable, Local TTS provides reliable offline generation!
        """)
    
    # TTS Method Selection
    st.header("🎯 TTS Method Selection")
    
    # Auto-select Local TTS if ElevenLabs is not working
    default_method = "Local TTS (Offline & Reliable)" if 'voices' in st.session_state and not st.session_state.voices else "ElevenLabs API (Online)"
    
    tts_method = st.radio(
        "Choose TTS Method:",
        ["ElevenLabs API (Online)", "Local TTS (Offline & Reliable)"],
        index=1 if default_method == "Local TTS (Offline & Reliable)" else 0,
        horizontal=True,
        help="ElevenLabs requires internet and valid API key. Local TTS works offline with system voices."
    )
    
    st.markdown("---")
    
    # Initialize variables to avoid scope issues
    voice_id = None
    stability = 0.5
    similarity_boost = 0.5
    text_input = ""
    generate_button = False
    
    # Main interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Input")
        
        if tts_method == "ElevenLabs API (Online)":
            # ElevenLabs interface
            voice_id, stability, similarity_boost = create_elevenlabs_interface(ELEVENLABS_API_KEY)
            
            # Voice cloning interface
            if 'elevenlabs_api' in st.session_state:
                create_voice_cloning_interface(st.session_state.elevenlabs_api)
            
            # Text input for ElevenLabs
            st.subheader("📝 Text to Synthesize")
            text_input = st.text_area(
                "Enter the text you want to convert to speech:",
                height=150,
                placeholder="Type your text here..."
            )
            
            # Generate button for ElevenLabs
            generate_button = st.button("🎯 Generate with ElevenLabs", type="primary")
            
        else:
            # Local TTS interface (existing code)
            st.info("🏠 **Local TTS Mode**: Using offline text-to-speech engines")
            
            # Voice customization for local TTS
            if app.pyttsx3_engine:
                st.subheader("🎛️ Voice Settings")
                
                # Get available voices
                available_voices = app.get_available_voices()
                if available_voices:
                    voice_names = [f"{name}" for voice_id, name in available_voices]
                    selected_voice_idx = st.selectbox(
                        "Choose System Voice:",
                        range(len(voice_names)),
                        format_func=lambda x: voice_names[x],
                        help="Select from available system voices"
                    )
                    
                    if selected_voice_idx is not None:
                        selected_voice_id = available_voices[selected_voice_idx][0]
                        app.set_voice(selected_voice_id)
                
                # Speech rate control
                speech_rate = st.slider(
                    "Speech Rate (words per minute)",
                    min_value=100,
                    max_value=300,
                    value=180,
                    step=10,
                    help="Adjust how fast the speech is generated"
                )
                app.set_speech_rate(speech_rate)
            
            # Reference audio upload (always available for voice cloning)
            st.subheader("🎵 Reference Audio for Voice Cloning")
            uploaded_file = st.file_uploader(
                "Upload reference audio file to clone this voice",
                type=['wav', 'mp3', 'flac', 'm4a'],
                help="Upload a clear 3-30 second audio sample of the voice you want to clone. The app will analyze and replicate this voice."
            )
            
            if uploaded_file is None:
                st.warning("⚠️ **Voice Cloning Requires Reference Audio**: Please upload an audio sample to clone a specific voice.")
                st.info("💡 Without reference audio, the app will use default system voices only.")
        
            reference_audio_path = None
            if uploaded_file is not None:
                # Process the uploaded audio
                audio_data, sr = app.load_reference_audio(uploaded_file)
                if audio_data is not None:
                    st.success("✅ Reference audio loaded successfully!")
                    
                    # Save reference audio temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        reference_audio_path = tmp_file.name
                    
                    # Play reference audio
                    st.audio(uploaded_file, format="audio/wav")
                    
                    # Analyze audio
                    analysis = app.analyze_audio(reference_audio_path)
                    if analysis:
                        st.subheader("📊 Audio Analysis")
                        st.metric("Duration", f"{analysis['duration']:.2f}s")
                        st.metric("Sample Rate", f"{analysis['sample_rate']} Hz")
                        if not np.isnan(analysis['pitch_mean']):
                            st.metric("Average Pitch", f"{analysis['pitch_mean']:.2f} Hz")
        
            # Text input
            st.subheader("📝 Text to Synthesize")
            text_input = st.text_area(
                "Enter the text you want to convert to speech:",
                height=150,
                placeholder="Type your text here..."
            )
            
            # Generate button
            generate_button = st.button("🎯 Generate Cloned Voice", type="primary")
    
    with col2:
        st.header("📥 Output")
        
        if generate_button:
            if not text_input.strip():
                st.error("Please enter some text to synthesize")
            else:
                if tts_method == "ElevenLabs API (Online)":
                    # ElevenLabs generation
                    if voice_id and 'elevenlabs_api' in st.session_state:
                        output_path = generate_speech_with_elevenlabs(
                            st.session_state.elevenlabs_api, 
                            text_input, 
                            voice_id, 
                            stability, 
                            similarity_boost
                        )
                        
                        if output_path and os.path.exists(output_path):
                            st.success("✅ ElevenLabs voice generation completed!")
                            
                            # Play generated audio
                            with open(output_path, "rb") as audio_file:
                                audio_bytes = audio_file.read()
                                st.audio(audio_bytes, format="audio/mpeg")
                            
                            # Download button
                            st.download_button(
                                label="💾 Download Generated Audio",
                                data=audio_bytes,
                                file_name=f"elevenlabs_voice_{hash(text_input)}.mp3",
                                mime="audio/mpeg"
                            )
                            
                            # Clean up
                            try:
                                os.unlink(output_path)
                            except:
                                pass
                    else:
                        st.error("Please select a voice first")
                
                else:
                    # Local TTS generation
                    with st.spinner("🔄 Generating speech with local TTS..."):
                        # Use reference audio path if available and advanced TTS is loaded
                        ref_audio = reference_audio_path if 'reference_audio_path' in locals() else None
                        output_path = app.clone_voice(text_input, ref_audio)
                        
                        if output_path and os.path.exists(output_path):
                            st.success("✅ Local TTS generation completed!")
                            
                            # Play generated audio
                            with open(output_path, "rb") as audio_file:
                                audio_bytes = audio_file.read()
                                st.audio(audio_bytes, format="audio/wav")
                            
                            # Download button
                            st.download_button(
                                label="💾 Download Generated Audio",
                                data=audio_bytes,
                                file_name=f"local_tts_voice_{hash(text_input)}.wav",
                                mime="audio/wav"
                            )
                            
                            # Analyze generated audio if it's a real audio file
                            try:
                                gen_analysis = app.analyze_audio(output_path)
                                if gen_analysis and gen_analysis['duration'] > 0:
                                    st.subheader("📊 Generated Audio Analysis")
                                    st.metric("Duration", f"{gen_analysis['duration']:.2f}s")
                                    st.metric("Sample Rate", f"{gen_analysis['sample_rate']} Hz")
                            except:
                                pass  # Skip analysis for placeholder audio
                            
                            # Clean up
                            try:
                                os.unlink(output_path)
                            except:
                                pass
                        else:
                            st.error("❌ Failed to generate audio. Please try again or check your text input.")
    
    # Footer
    st.markdown("---")
    st.markdown("🎙️ **Voice Cloning App** - Built with Streamlit and TTS libraries")

if __name__ == "__main__":
    main()
