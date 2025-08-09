import requests
import streamlit as st
import tempfile
import os
from typing import List, Dict, Optional
import json

class ElevenLabsAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
    
    def get_voices(self) -> List[Dict]:
        """Get available voices from ElevenLabs"""
        try:
            url = f"{self.base_url}/voices"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json().get("voices", [])
            elif response.status_code == 401:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                if 'detected_unusual_activity' in str(error_data):
                    st.warning("⚠️ ElevenLabs API access restricted. Using Local TTS mode.")
                else:
                    st.warning("🔑 ElevenLabs API authentication failed.")
                return []
            else:
                st.warning(f"⚠️ Could not fetch ElevenLabs voices: {response.status_code}")
                return []
        
        except Exception as e:
            st.warning(f"🔌 Network error fetching voices: {str(e)}")
            return []
    
    def text_to_speech(self, text: str, voice_id: str, model_id: str = "eleven_monolingual_v1") -> Optional[bytes]:
        """Convert text to speech using ElevenLabs API"""
        try:
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            
            data = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 401:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                if 'detected_unusual_activity' in str(error_data):
                    st.error("🚫 ElevenLabs Free Tier Blocked: Unusual activity detected. Please use Local TTS instead or upgrade to a paid plan.")
                    st.info("💡 **Tip**: Switch to 'Local TTS' mode below for offline voice generation.")
                else:
                    st.error(f"🔑 Authentication failed: Invalid API key or quota exceeded")
                return None
            elif response.status_code == 429:
                st.error("⏰ Rate limit exceeded. Please wait a moment and try again.")
                return None
            else:
                st.error(f"❌ TTS failed: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            st.error(f"🔌 Network error in text-to-speech: {str(e)}")
            return None
    
    def clone_voice(self, name: str, description: str, files: List[bytes]) -> Optional[str]:
        """Clone a voice using uploaded audio files"""
        try:
            url = f"{self.base_url}/voices/add"
            
            # Prepare files for upload
            files_data = []
            for i, file_content in enumerate(files):
                files_data.append(('files', (f'sample_{i}.wav', file_content, 'audio/wav')))
            
            data = {
                'name': name,
                'description': description
            }
            
            # Remove content-type from headers for multipart upload
            headers = {key: value for key, value in self.headers.items() if key != "Content-Type"}
            
            response = requests.post(url, data=data, files=files_data, headers=headers)
            
            if response.status_code == 200:
                voice_data = response.json()
                return voice_data.get("voice_id")
            else:
                st.error(f"Voice cloning failed: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            st.error(f"Error in voice cloning: {str(e)}")
            return None
    
    def get_voice_settings(self, voice_id: str) -> Optional[Dict]:
        """Get voice settings for a specific voice"""
        try:
            url = f"{self.base_url}/voices/{voice_id}/settings"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        
        except Exception as e:
            st.error(f"Error fetching voice settings: {str(e)}")
            return None
    
    def update_voice_settings(self, voice_id: str, stability: float, similarity_boost: float) -> bool:
        """Update voice settings"""
        try:
            url = f"{self.base_url}/voices/{voice_id}/settings/edit"
            
            data = {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
            
            response = requests.post(url, json=data, headers=self.headers)
            return response.status_code == 200
        
        except Exception as e:
            st.error(f"Error updating voice settings: {str(e)}")
            return False
    
    def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice"""
        try:
            url = f"{self.base_url}/voices/{voice_id}"
            response = requests.delete(url, headers=self.headers)
            return response.status_code == 200
        
        except Exception as e:
            st.error(f"Error deleting voice: {str(e)}")
            return False
    
    def get_user_info(self) -> Optional[Dict]:
        """Get user information and usage stats"""
        try:
            url = f"{self.base_url}/user"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        
        except Exception as e:
            st.error(f"Error fetching user info: {str(e)}")
            return None

def create_elevenlabs_interface(api_key: str):
    """Create ElevenLabs interface components"""
    
    # Initialize ElevenLabs API
    if 'elevenlabs_api' not in st.session_state:
        st.session_state.elevenlabs_api = ElevenLabsAPI(api_key)
    
    api = st.session_state.elevenlabs_api
    
    # Get user info
    user_info = api.get_user_info()
    if user_info:
        st.sidebar.success(f"✅ ElevenLabs Connected")
        st.sidebar.info(f"Characters used: {user_info.get('character_count', 0)}")
        st.sidebar.info(f"Character limit: {user_info.get('character_limit', 0)}")
    else:
        st.sidebar.warning("⚠️ ElevenLabs API Issue")
        st.sidebar.info("💡 Consider using Local TTS instead")
    
    # Voice selection
    st.subheader("🎭 Voice Selection")
    
    # Get available voices
    if 'voices' not in st.session_state:
        with st.spinner("Loading voices..."):
            st.session_state.voices = api.get_voices()
    
    voices = st.session_state.voices
    
    if voices:
        voice_options = {f"{voice['name']} ({voice['category']})": voice['voice_id'] 
                        for voice in voices}
        
        selected_voice_name = st.selectbox(
            "Choose a voice:",
            options=list(voice_options.keys()),
            help="Select from available ElevenLabs voices"
        )
        
        selected_voice_id = voice_options[selected_voice_name]
        
        # Voice settings
        col1, col2 = st.columns(2)
        with col1:
            stability = st.slider("Stability", 0.0, 1.0, 0.5, 0.1)
        with col2:
            similarity_boost = st.slider("Similarity Boost", 0.0, 1.0, 0.5, 0.1)
        
        return selected_voice_id, stability, similarity_boost
    
    else:
        st.warning("⚠️ ElevenLabs voices unavailable. Please use Local TTS mode below.")
        st.info("🔄 **Recommendation**: Switch to 'Local TTS (Coqui/pyttsx3)' for offline voice generation.")
        return None, None, None

def create_voice_cloning_interface(api: ElevenLabsAPI):
    """Create voice cloning interface"""
    st.subheader("🎙️ Voice Cloning")
    
    with st.expander("Clone New Voice", expanded=False):
        voice_name = st.text_input("Voice Name", placeholder="Enter a name for your cloned voice")
        voice_description = st.text_area("Description", placeholder="Describe the voice characteristics")
        
        uploaded_files = st.file_uploader(
            "Upload Audio Samples",
            type=['wav', 'mp3', 'flac'],
            accept_multiple_files=True,
            help="Upload 2-5 clear audio samples (each 1-30 seconds)"
        )
        
        if st.button("🔄 Clone Voice") and voice_name and uploaded_files:
            if len(uploaded_files) < 2:
                st.error("Please upload at least 2 audio samples")
            else:
                with st.spinner("Cloning voice... This may take a few minutes."):
                    # Prepare audio files
                    audio_files = []
                    for uploaded_file in uploaded_files:
                        audio_files.append(uploaded_file.getvalue())
                    
                    # Clone voice
                    voice_id = api.clone_voice(voice_name, voice_description, audio_files)
                    
                    if voice_id:
                        st.success(f"✅ Voice cloned successfully! Voice ID: {voice_id}")
                        # Refresh voices list
                        st.session_state.voices = api.get_voices()
                        st.rerun()
                    else:
                        st.error("❌ Voice cloning failed")

def generate_speech_with_elevenlabs(api: ElevenLabsAPI, text: str, voice_id: str, 
                                  stability: float, similarity_boost: float) -> Optional[str]:
    """Generate speech using ElevenLabs API"""
    if not text.strip():
        st.error("Please enter text to synthesize")
        return None
    
    # Update voice settings
    api.update_voice_settings(voice_id, stability, similarity_boost)
    
    # Generate speech
    with st.spinner("🔄 Generating speech with ElevenLabs..."):
        audio_content = api.text_to_speech(text, voice_id)
        
        if audio_content:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_content)
                return tmp_file.name
        
        return None
