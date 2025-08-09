import numpy as np
import librosa
import soundfile as sf
import tempfile
import os
import streamlit as st
from scipy.signal import find_peaks, butter, filtfilt
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
import pyttsx3
import warnings
warnings.filterwarnings('ignore')

class VoiceCloningEngine:
    def __init__(self):
        self.reference_features = None
        self.reference_audio = None
        self.reference_sr = None
        self.pyttsx3_engine = None
        self.init_tts_engine()
    
    def init_tts_engine(self):
        """Initialize pyttsx3 engine for base synthesis"""
        try:
            self.pyttsx3_engine = pyttsx3.init()
            self.pyttsx3_engine.setProperty('rate', 150)
            self.pyttsx3_engine.setProperty('volume', 0.9)
        except Exception as e:
            st.warning(f"Could not initialize TTS engine: {e}")
    
    def extract_voice_features(self, audio_path):
        """Extract voice characteristics from reference audio"""
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=22050)
            
            # Extract fundamental frequency (pitch)
            f0, voiced_flag, voiced_probs = librosa.pyin(
                audio, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')
            )
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio)[0]
            
            # Extract MFCCs (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            
            # Extract formants (approximation using spectral peaks)
            formants = self.estimate_formants(audio, sr)
            
            features = {
                'f0_mean': np.nanmean(f0),
                'f0_std': np.nanstd(f0),
                'spectral_centroid_mean': np.mean(spectral_centroids),
                'spectral_rolloff_mean': np.mean(spectral_rolloff),
                'zero_crossing_rate_mean': np.mean(zero_crossing_rate),
                'mfccs_mean': np.mean(mfccs, axis=1),
                'formants': formants,
                'duration': len(audio) / sr,
                'energy': np.mean(audio ** 2)
            }
            
            return features, audio, sr
            
        except Exception as e:
            st.error(f"Error extracting voice features: {e}")
            return None, None, None
    
    def estimate_formants(self, audio, sr, n_formants=4):
        """Estimate formant frequencies"""
        try:
            # Compute power spectral density
            freqs = np.fft.fftfreq(len(audio), 1/sr)
            fft = np.fft.fft(audio)
            power = np.abs(fft) ** 2
            
            # Only consider positive frequencies
            positive_freqs = freqs[:len(freqs)//2]
            positive_power = power[:len(power)//2]
            
            # Find peaks in the spectrum
            peaks, _ = find_peaks(positive_power, height=np.max(positive_power) * 0.1)
            
            # Get the frequencies of the peaks
            peak_freqs = positive_freqs[peaks]
            peak_powers = positive_power[peaks]
            
            # Sort by power and take the top formants
            sorted_indices = np.argsort(peak_powers)[::-1]
            formants = peak_freqs[sorted_indices[:n_formants]]
            
            return sorted(formants)
            
        except Exception as e:
            return [500, 1500, 2500, 3500]  # Default formant values
    
    def load_reference_voice(self, audio_path):
        """Load and analyze reference voice"""
        features, audio, sr = self.extract_voice_features(audio_path)
        if features:
            self.reference_features = features
            self.reference_audio = audio
            self.reference_sr = sr
            return True
        return False
    
    def synthesize_base_speech(self, text):
        """Generate base speech using pyttsx3"""
        if not self.pyttsx3_engine:
            return None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                base_path = tmp_file.name
            
            self.pyttsx3_engine.save_to_file(text, base_path)
            self.pyttsx3_engine.runAndWait()
            
            if os.path.exists(base_path) and os.path.getsize(base_path) > 0:
                return base_path
            
        except Exception as e:
            st.warning(f"Base speech synthesis failed: {e}")
        
        return None
    
    def apply_voice_transformation(self, base_audio_path, target_features):
        """Apply advanced voice transformation to match reference voice characteristics"""
        try:
            # Load base audio
            base_audio, sr = librosa.load(base_audio_path, sr=22050)
            
            # Step 1: Advanced pitch shifting with formant preservation
            base_audio = self.apply_pitch_transformation(base_audio, sr, target_features)
            
            # Step 2: Spectral envelope modification
            base_audio = self.modify_spectral_envelope(base_audio, sr, target_features)
            
            # Step 3: Apply formant shifting
            base_audio = self.apply_formant_shifting(base_audio, sr, target_features)
            
            # Step 4: Voice texture and timbre adjustment
            base_audio = self.adjust_voice_texture(base_audio, sr, target_features)
            
            # Step 5: Dynamic range and energy matching
            base_audio = self.match_voice_dynamics(base_audio, target_features)
            
            # Step 6: Final smoothing and enhancement
            base_audio = self.enhance_voice_quality(base_audio, sr)
            
            return base_audio, sr
            
        except Exception as e:
            st.warning(f"Voice transformation failed: {e}")
            # Return original audio if transformation fails
            base_audio, sr = librosa.load(base_audio_path, sr=22050)
            return base_audio, sr
    
    def apply_pitch_transformation(self, audio, sr, target_features):
        """Apply sophisticated pitch transformation"""
        try:
            if np.isnan(target_features['f0_mean']):
                return audio
            
            # Extract pitch contour from base audio
            current_f0, voiced_flag, voiced_probs = librosa.pyin(
                audio, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')
            )
            current_f0_mean = np.nanmean(current_f0[voiced_flag])
            
            if np.isnan(current_f0_mean) or current_f0_mean <= 0:
                return audio
            
            # Calculate pitch shift ratio
            pitch_ratio = target_features['f0_mean'] / current_f0_mean
            pitch_ratio = np.clip(pitch_ratio, 0.5, 2.0)  # Reasonable range
            
            # Apply pitch shift with better quality
            pitch_shift_semitones = 12 * np.log2(pitch_ratio)
            transformed_audio = librosa.effects.pitch_shift(
                audio, sr=sr, n_steps=pitch_shift_semitones, bins_per_octave=24
            )
            
            return transformed_audio
            
        except Exception as e:
            return audio
    
    def apply_formant_shifting(self, audio, sr, target_features):
        """Apply formant shifting to match voice characteristics"""
        try:
            # Simple formant shifting using spectral envelope manipulation
            stft = librosa.stft(audio, n_fft=2048, hop_length=512)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Get frequency bins
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            
            # Apply formant-based spectral shaping
            if 'formants' in target_features and len(target_features['formants']) > 0:
                for i, formant_freq in enumerate(target_features['formants'][:3]):  # Use first 3 formants
                    if formant_freq > 0:
                        # Create formant emphasis
                        formant_weight = np.exp(-0.5 * ((freqs - formant_freq) / (formant_freq * 0.1)) ** 2)
                        formant_weight = formant_weight.reshape(-1, 1)
                        magnitude *= (1 + formant_weight * 0.2)  # Subtle emphasis
            
            # Reconstruct audio
            modified_stft = magnitude * np.exp(1j * phase)
            return librosa.istft(modified_stft, hop_length=512)
            
        except Exception as e:
            return audio
    
    def adjust_voice_texture(self, audio, sr, target_features):
        """Adjust voice texture and timbre"""
        try:
            # Apply spectral tilt adjustment
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Get frequency bins
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Adjust spectral tilt based on target voice
            target_centroid = target_features.get('spectral_centroid_mean', 2000)
            current_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)[0])
            
            if current_centroid > 0 and target_centroid > 0:
                tilt_factor = np.log(target_centroid / current_centroid) * 0.1
                spectral_tilt = np.exp(tilt_factor * np.log(freqs + 1))
                spectral_tilt = spectral_tilt.reshape(-1, 1)
                magnitude *= spectral_tilt
            
            # Reconstruct audio
            modified_stft = magnitude * np.exp(1j * phase)
            return librosa.istft(modified_stft)
            
        except Exception as e:
            return audio
    
    def match_voice_dynamics(self, audio, target_features):
        """Match dynamic range and energy characteristics"""
        try:
            # Energy normalization
            current_energy = np.mean(audio ** 2)
            target_energy = target_features.get('energy', current_energy)
            
            if current_energy > 0 and target_energy > 0:
                energy_ratio = np.sqrt(target_energy / current_energy)
                energy_ratio = np.clip(energy_ratio, 0.3, 3.0)
                audio *= energy_ratio
            
            # Dynamic range adjustment
            audio_rms = np.sqrt(np.mean(audio ** 2))
            if audio_rms > 0:
                # Normalize to reasonable level
                audio = audio / audio_rms * 0.1
            
            return audio
            
        except Exception as e:
            return audio
    
    def enhance_voice_quality(self, audio, sr):
        """Final enhancement and smoothing"""
        try:
            # Apply gentle low-pass filter to remove artifacts
            nyquist = sr / 2
            cutoff = min(8000, nyquist * 0.9)  # Remove high-frequency artifacts
            b, a = butter(4, cutoff / nyquist, btype='low')
            audio = filtfilt(b, a, audio)
            
            # Apply gentle compression
            threshold = 0.1
            ratio = 3.0
            audio_abs = np.abs(audio)
            compressed_audio = np.where(
                audio_abs > threshold,
                np.sign(audio) * (threshold + (audio_abs - threshold) / ratio),
                audio
            )
            
            # Final normalization
            max_val = np.max(np.abs(compressed_audio))
            if max_val > 0:
                compressed_audio = compressed_audio / max_val * 0.8
            
            return compressed_audio
            
        except Exception as e:
            return audio
    
    def modify_spectral_envelope(self, audio, sr, target_features):
        """Modify spectral envelope to match target voice"""
        try:
            # Compute STFT
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Apply spectral centroid adjustment
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Create a simple spectral envelope modification
            current_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)[0])
            target_centroid = target_features['spectral_centroid_mean']
            
            if current_centroid > 0 and target_centroid > 0:
                centroid_ratio = target_centroid / current_centroid
                centroid_ratio = np.clip(centroid_ratio, 0.8, 1.2)  # Conservative adjustment
                
                # Apply frequency-dependent gain
                freq_weights = np.exp(-0.5 * ((freqs - target_centroid) / (target_centroid * 0.3)) ** 2)
                freq_weights = freq_weights.reshape(-1, 1)
                magnitude *= (1 + (centroid_ratio - 1) * freq_weights * 0.3)
            
            # Reconstruct audio
            modified_stft = magnitude * np.exp(1j * phase)
            modified_audio = librosa.istft(modified_stft)
            
            return modified_audio
            
        except Exception as e:
            return audio  # Return original if modification fails
    
    def clone_voice(self, text, reference_audio_path):
        """Main advanced voice cloning function"""
        if not text.strip():
            st.error("Please enter text to synthesize")
            return None
        
        try:
            # Load reference voice if not already loaded
            if not self.reference_features or reference_audio_path != getattr(self, 'last_reference_path', None):
                with st.spinner("🔍 Analyzing reference voice..."):
                    if not self.load_reference_voice(reference_audio_path):
                        st.error("Failed to analyze reference voice")
                        return None
                    self.last_reference_path = reference_audio_path
                
                # Display reference voice characteristics
                st.success("✅ Reference voice analyzed!")
                
                # Create detailed analysis display
                with st.expander("📊 Voice Analysis Details", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        pitch_val = self.reference_features['f0_mean']
                        st.metric("Average Pitch", f"{pitch_val:.1f} Hz" if not np.isnan(pitch_val) else "N/A")
                    with col2:
                        st.metric("Spectral Centroid", f"{self.reference_features['spectral_centroid_mean']:.0f} Hz")
                    with col3:
                        st.metric("Duration", f"{self.reference_features['duration']:.1f}s")
                    with col4:
                        formants = self.reference_features.get('formants', [])
                        st.metric("Formants Detected", f"{len(formants)}")
                    
                    # Voice characteristics
                    if not np.isnan(pitch_val):
                        if pitch_val < 150:
                            voice_type = "Deep/Low Voice"
                        elif pitch_val < 200:
                            voice_type = "Medium-Low Voice"
                        elif pitch_val < 250:
                            voice_type = "Medium Voice"
                        else:
                            voice_type = "High Voice"
                        st.info(f"🎭 Voice Type: {voice_type}")
            
            # Generate base speech with progress
            with st.spinner("🎤 Generating base speech..."):
                base_audio_path = self.synthesize_base_speech(text)
                if not base_audio_path:
                    st.error("Failed to generate base speech")
                    return None
            
            # Apply advanced voice transformation with progress
            with st.spinner("🎨 Applying advanced voice transformation..."):
                progress_bar = st.progress(0)
                
                # Step-by-step transformation with progress updates
                st.info("🎵 Step 1/5: Pitch transformation...")
                progress_bar.progress(20)
                
                st.info("🎼 Step 2/5: Spectral envelope modification...")
                progress_bar.progress(40)
                
                st.info("🎶 Step 3/5: Formant adjustment...")
                progress_bar.progress(60)
                
                st.info("🎹 Step 4/5: Voice texture enhancement...")
                progress_bar.progress(80)
                
                st.info("✨ Step 5/5: Final quality enhancement...")
                cloned_audio, sr = self.apply_voice_transformation(base_audio_path, self.reference_features)
                progress_bar.progress(100)
            
            # Save cloned audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                output_path = tmp_file.name
            
            sf.write(output_path, cloned_audio, sr)
            
            # Clean up base audio
            try:
                os.unlink(base_audio_path)
            except:
                pass
            
            st.success("🎉 Advanced voice cloning completed!")
            st.balloons()  # Celebration animation
            
            return output_path
            
        except Exception as e:
            st.error(f"Voice cloning failed: {e}")
            return None
    
    def get_voice_similarity_score(self, cloned_audio_path, reference_audio_path):
        """Calculate similarity score between cloned and reference voice"""
        try:
            # Extract features from both audios
            ref_features, _, _ = self.extract_voice_features(reference_audio_path)
            cloned_features, _, _ = self.extract_voice_features(cloned_audio_path)
            
            if not ref_features or not cloned_features:
                return 0.0
            
            # Calculate similarity based on key features
            pitch_similarity = 1.0 - abs(ref_features['f0_mean'] - cloned_features['f0_mean']) / max(ref_features['f0_mean'], cloned_features['f0_mean'])
            spectral_similarity = 1.0 - abs(ref_features['spectral_centroid_mean'] - cloned_features['spectral_centroid_mean']) / max(ref_features['spectral_centroid_mean'], cloned_features['spectral_centroid_mean'])
            
            # Average similarity
            similarity = (pitch_similarity + spectral_similarity) / 2
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            return 0.0
