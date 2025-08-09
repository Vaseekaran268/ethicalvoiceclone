import streamlit as st
import numpy as np
import librosa
import soundfile as sf
import tempfile
import os
import hashlib
import datetime
from datetime import timedelta
import time
import re
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import our modules
from auth import AuthManager, show_login_page, show_signup_page, check_authentication, logout
from voice_cloning_engine import VoiceCloningEngine

# Profanity filter - basic implementation
BLOCKED_WORDS = [
    'scam', 'fraud', 'impersonate', 'fake', 'deceive', 'cheat', 'lie', 'steal',
    'hack', 'phishing', 'spam', 'illegal', 'criminal', 'threat', 'blackmail'
]

class EthicalVoiceCloningPlatform:
    def __init__(self):
        self.voice_engine = VoiceCloningEngine()
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        if 'current_step' not in st.session_state:
            st.session_state.current_step = 'landing'
        if 'voice_sample' not in st.session_state:
            st.session_state.voice_sample = None
        if 'voice_sample_path' not in st.session_state:
            st.session_state.voice_sample_path = None
        if 'text_input' not in st.session_state:
            st.session_state.text_input = ""
        if 'consent_given' not in st.session_state:
            st.session_state.consent_given = False
        if 'generated_audio' not in st.session_state:
            st.session_state.generated_audio = None
        if 'audio_quality_score' not in st.session_state:
            st.session_state.audio_quality_score = 0
        if 'noise_removed' not in st.session_state:
            st.session_state.noise_removed = False
    
    def check_audio_quality(self, audio_path):
        """Analyze audio quality and detect issues"""
        try:
            audio, sr = librosa.load(audio_path, sr=22050)
            
            # Calculate quality metrics
            duration = len(audio) / sr
            rms_energy = np.sqrt(np.mean(audio ** 2))
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio)[0])
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)[0])
            
            # Quality scoring
            quality_score = 0
            issues = []
            
            # Duration check
            if 3 <= duration <= 15:
                quality_score += 25
            else:
                issues.append(f"Duration should be 3-15 seconds (current: {duration:.1f}s)")
            
            # Energy check
            if 0.01 <= rms_energy <= 0.5:
                quality_score += 25
            elif rms_energy < 0.01:
                issues.append("Audio too quiet - increase volume")
            else:
                issues.append("Audio too loud - may be clipped")
            
            # Noise check (simplified)
            if zero_crossing_rate < 0.3:
                quality_score += 25
            else:
                issues.append("High background noise detected")
            
            # Spectral quality
            if 1000 <= spectral_centroid <= 4000:
                quality_score += 25
            else:
                issues.append("Poor spectral quality - use clearer recording")
            
            return quality_score, issues, {
                'duration': duration,
                'rms_energy': rms_energy,
                'zero_crossing_rate': zero_crossing_rate,
                'spectral_centroid': spectral_centroid
            }
            
        except Exception as e:
            return 0, [f"Error analyzing audio: {str(e)}"], {}
    
    def remove_noise(self, audio_path):
        """Simple noise removal using spectral gating"""
        try:
            audio, sr = librosa.load(audio_path, sr=22050)
            
            # Simple noise reduction using spectral subtraction
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Estimate noise floor from first 0.5 seconds
            noise_frames = int(0.5 * sr / 512)  # 512 is hop_length
            noise_spectrum = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
            
            # Apply spectral subtraction
            alpha = 2.0  # Over-subtraction factor
            cleaned_magnitude = magnitude - alpha * noise_spectrum
            cleaned_magnitude = np.maximum(cleaned_magnitude, 0.1 * magnitude)
            
            # Reconstruct audio
            cleaned_stft = cleaned_magnitude * np.exp(1j * phase)
            cleaned_audio = librosa.istft(cleaned_stft)
            
            # Save cleaned audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                cleaned_path = tmp_file.name
            sf.write(cleaned_path, cleaned_audio, sr)
            
            return cleaned_path, True
            
        except Exception as e:
            st.error(f"Noise removal failed: {e}")
            return audio_path, False
    
    def check_profanity(self, text):
        """Check for blocked words and profanity"""
        text_lower = text.lower()
        found_words = []
        
        for word in BLOCKED_WORDS:
            if word in text_lower:
                found_words.append(word)
        
        return found_words
    
    def add_watermark(self, audio_path):
        """Add inaudible watermark to audio"""
        try:
            audio, sr = librosa.load(audio_path, sr=22050)
            
            # Create watermark data
            timestamp = datetime.datetime.now().isoformat()
            user_id = st.session_state.get('user', {}).get('id', 'anonymous')
            watermark_data = f"CLONED_{timestamp}_{user_id}"
            
            # Simple watermark: add very low amplitude high-frequency tone
            watermark_freq = 18000  # Near ultrasonic
            t = np.linspace(0, len(audio)/sr, len(audio), False)
            watermark_signal = 0.001 * np.sin(2 * np.pi * watermark_freq * t)
            
            # Add watermark
            watermarked_audio = audio + watermark_signal
            
            # Save watermarked audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                watermarked_path = tmp_file.name
            sf.write(watermarked_path, watermarked_audio, sr)
            
            return watermarked_path, watermark_data
            
        except Exception as e:
            st.error(f"Watermarking failed: {e}")
            return audio_path, "WATERMARK_FAILED"
    
    def create_waveform_comparison(self, original_path, cleaned_path):
        """Create before/after waveform comparison"""
        try:
            # Load both audio files
            original_audio, sr1 = librosa.load(original_path, sr=22050)
            cleaned_audio, sr2 = librosa.load(cleaned_path, sr=22050)
            
            # Create time axes
            time_original = np.linspace(0, len(original_audio)/sr1, len(original_audio))
            time_cleaned = np.linspace(0, len(cleaned_audio)/sr2, len(cleaned_audio))
            
            # Create subplot
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Original Audio', 'Noise-Removed Audio'),
                vertical_spacing=0.1
            )
            
            # Add original waveform
            fig.add_trace(
                go.Scatter(x=time_original, y=original_audio, 
                          name='Original', line=dict(color='red', width=1)),
                row=1, col=1
            )
            
            # Add cleaned waveform
            fig.add_trace(
                go.Scatter(x=time_cleaned, y=cleaned_audio, 
                          name='Cleaned', line=dict(color='green', width=1)),
                row=2, col=1
            )
            
            fig.update_layout(
                height=400,
                title_text="Audio Quality Improvement",
                showlegend=False
            )
            
            fig.update_xaxes(title_text="Time (seconds)")
            fig.update_yaxes(title_text="Amplitude")
            
            return fig
            
        except Exception as e:
            st.error(f"Could not create waveform comparison: {e}")
            return None
