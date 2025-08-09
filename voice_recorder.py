import streamlit as st
import numpy as np
import tempfile
import os
import time
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import threading
import queue
import soundfile as sf

class VoiceRecorder:
    def __init__(self):
        self.audio_frames = []
        self.recording = False
        self.audio_queue = queue.Queue()
        
    def audio_frame_callback(self, frame):
        """Callback to process audio frames during recording"""
        if self.recording:
            audio_array = frame.to_ndarray()
            self.audio_queue.put(audio_array)
        return frame
    
    def start_recording(self):
        """Start recording audio"""
        self.recording = True
        self.audio_frames = []
        
    def stop_recording(self):
        """Stop recording and return audio data"""
        self.recording = False
        
        # Collect all audio frames
        audio_data = []
        while not self.audio_queue.empty():
            try:
                frame = self.audio_queue.get_nowait()
                audio_data.append(frame)
            except queue.Empty:
                break
        
        if audio_data:
            # Concatenate all frames
            full_audio = np.concatenate(audio_data, axis=0)
            return full_audio
        return None
    
    def save_recording(self, audio_data, sample_rate=48000):
        """Save recorded audio to temporary file"""
        if audio_data is None or len(audio_data) == 0:
            return None
            
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                temp_path = tmp_file.name
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Normalize audio
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
            
            # Save as WAV file
            sf.write(temp_path, audio_data, sample_rate)
            return temp_path
            
        except Exception as e:
            st.error(f"Error saving recording: {e}")
            return None

def show_voice_recorder():
    """Show the voice recording interface"""
    st.subheader("🎤 Record Your Voice Live")
    
    # WebRTC configuration
    rtc_configuration = RTCConfiguration({
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    })
    
    # Initialize recorder
    if 'voice_recorder' not in st.session_state:
        st.session_state.voice_recorder = VoiceRecorder()
    
    recorder = st.session_state.voice_recorder
    
    # Recording controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔴 Start Recording", type="primary"):
            st.session_state.is_recording = True
            recorder.start_recording()
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Recording", disabled=not st.session_state.get('is_recording', False)):
            st.session_state.is_recording = False
            audio_data = recorder.stop_recording()
            
            if audio_data is not None:
                # Save the recording
                audio_path = recorder.save_recording(audio_data)
                if audio_path:
                    st.session_state.recorded_audio_path = audio_path
                    st.success("✅ Recording saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save recording")
            else:
                st.warning("⚠️ No audio data recorded")
    
    with col3:
        if st.button("🗑️ Clear Recording"):
            if 'recorded_audio_path' in st.session_state:
                try:
                    if os.path.exists(st.session_state.recorded_audio_path):
                        os.unlink(st.session_state.recorded_audio_path)
                except:
                    pass
                del st.session_state.recorded_audio_path
            st.session_state.is_recording = False
            st.rerun()
    
    # Recording status
    if st.session_state.get('is_recording', False):
        st.error("🔴 **RECORDING IN PROGRESS** - Speak clearly into your microphone")
        
        # Show recording timer
        if 'recording_start_time' not in st.session_state:
            st.session_state.recording_start_time = time.time()
        
        elapsed_time = time.time() - st.session_state.recording_start_time
        st.info(f"⏱️ Recording time: {elapsed_time:.1f} seconds")
        
        # Auto-stop after 15 seconds
        if elapsed_time > 15:
            st.warning("⚠️ Maximum recording time (15s) reached. Stopping automatically...")
            st.session_state.is_recording = False
            audio_data = recorder.stop_recording()
            
            if audio_data is not None:
                audio_path = recorder.save_recording(audio_data)
                if audio_path:
                    st.session_state.recorded_audio_path = audio_path
                    st.success("✅ Recording saved successfully!")
            
            time.sleep(1)
            st.rerun()
    
    # WebRTC streamer for audio capture
    if st.session_state.get('is_recording', False):
        webrtc_ctx = webrtc_streamer(
            key="voice-recorder",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=1024,
            rtc_configuration=rtc_configuration,
            media_stream_constraints={"video": False, "audio": True},
            audio_frame_callback=recorder.audio_frame_callback,
        )
    
    # Show recorded audio if available
    if 'recorded_audio_path' in st.session_state and os.path.exists(st.session_state.recorded_audio_path):
        st.success("🎧 **Your Recording:**")
        
        with open(st.session_state.recorded_audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/wav")
        
        # Return the path for use in main app
        return st.session_state.recorded_audio_path
    
    return None

def show_simple_recorder():
    """Simplified recorder using HTML5 audio recording"""
    st.subheader("🎤 Record Your Voice")
    
    # HTML5 Audio Recording Interface
    st.markdown("""
    <div style="text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 10px;">
        <h4>🎙️ Browser Voice Recorder</h4>
        <p>Click the button below to start recording (5-15 seconds recommended)</p>
        
        <button id="recordBtn" onclick="toggleRecording()" 
                style="background: #ff4444; color: white; border: none; padding: 10px 20px; 
                       border-radius: 5px; font-size: 16px; cursor: pointer;">
            🔴 Start Recording
        </button>
        
        <div id="status" style="margin-top: 10px; font-weight: bold;"></div>
        <audio id="audioPlayback" controls style="margin-top: 10px; display: none;"></audio>
    </div>
    
    <script>
    let mediaRecorder;
    let recordedChunks = [];
    let isRecording = false;
    
    async function toggleRecording() {
        const recordBtn = document.getElementById('recordBtn');
        const status = document.getElementById('status');
        const audioPlayback = document.getElementById('audioPlayback');
        
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'audio/wav' });
                    const audioURL = URL.createObjectURL(blob);
                    audioPlayback.src = audioURL;
                    audioPlayback.style.display = 'block';
                    
                    // Convert to base64 and send to Streamlit
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64data = reader.result.split(',')[1];
                        window.parent.postMessage({
                            type: 'audio_recorded',
                            data: base64data
                        }, '*');
                    };
                    reader.readAsDataURL(blob);
                };
                
                mediaRecorder.start();
                isRecording = true;
                recordBtn.innerHTML = '⏹️ Stop Recording';
                recordBtn.style.background = '#444';
                status.innerHTML = '🔴 Recording... Speak clearly!';
                
                // Auto-stop after 15 seconds
                setTimeout(() => {
                    if (isRecording) {
                        stopRecording();
                    }
                }, 15000);
                
            } catch (err) {
                status.innerHTML = '❌ Microphone access denied or not available';
                console.error('Error accessing microphone:', err);
            }
        } else {
            stopRecording();
        }
    }
    
    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            isRecording = false;
            
            const recordBtn = document.getElementById('recordBtn');
            const status = document.getElementById('status');
            
            recordBtn.innerHTML = '🔴 Start Recording';
            recordBtn.style.background = '#ff4444';
            status.innerHTML = '✅ Recording completed! Check the audio player below.';
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Instructions
    st.info("""
    **📋 Recording Instructions:**
    - Click "Start Recording" and allow microphone access
    - Speak clearly for 5-15 seconds
    - Recording will auto-stop after 15 seconds
    - You can manually stop anytime by clicking the button again
    """)
    
    return None
