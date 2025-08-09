import streamlit as st
import streamlit.components.v1 as components
import base64
import tempfile
import os
import numpy as np
import soundfile as sf
from io import BytesIO

def create_audio_recorder():
    """Create an advanced audio recorder component"""
    
    # HTML and JavaScript for audio recording
    recorder_html = """
    <div id="audioRecorder" style="text-align: center; padding: 20px; border: 2px solid #4CAF50; border-radius: 15px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);">
        <h3 style="color: #2E86AB; margin-bottom: 20px;">🎙️ Voice Recorder</h3>
        
        <div id="recordingControls">
            <button id="startBtn" onclick="startRecording()" 
                    style="background: #4CAF50; color: white; border: none; padding: 15px 25px; 
                           border-radius: 25px; font-size: 16px; cursor: pointer; margin: 5px;">
                🔴 Start Recording
            </button>
            
            <button id="stopBtn" onclick="stopRecording()" disabled
                    style="background: #f44336; color: white; border: none; padding: 15px 25px; 
                           border-radius: 25px; font-size: 16px; cursor: pointer; margin: 5px;">
                ⏹️ Stop Recording
            </button>
            
            <button id="playBtn" onclick="playRecording()" disabled
                    style="background: #2196F3; color: white; border: none; padding: 15px 25px; 
                           border-radius: 25px; font-size: 16px; cursor: pointer; margin: 5px;">
                ▶️ Play
            </button>
        </div>
        
        <div id="recordingStatus" style="margin: 15px 0; font-weight: bold; font-size: 18px;"></div>
        <div id="timer" style="font-size: 24px; font-weight: bold; color: #ff4444; margin: 10px;"></div>
        
        <canvas id="visualizer" width="400" height="100" style="border: 1px solid #ccc; margin: 15px; border-radius: 10px; background: #f9f9f9;"></canvas>
        
        <div id="audioContainer" style="margin: 15px;">
            <audio id="audioPlayback" controls style="width: 100%; max-width: 400px; display: none;"></audio>
        </div>
        
        <div id="uploadSection" style="display: none; margin-top: 20px;">
            <button id="uploadBtn" onclick="uploadRecording()" 
                    style="background: #FF9800; color: white; border: none; padding: 15px 30px; 
                           border-radius: 25px; font-size: 18px; cursor: pointer;">
                ✅ Use This Recording
            </button>
        </div>
        
        <div id="instructions" style="margin-top: 15px; color: #666; font-size: 14px;">
            📋 <strong>Instructions:</strong> Click "Start Recording", speak clearly for 5-15 seconds, then click "Stop". 
            Listen to your recording and click "Use This Recording" if you're satisfied.
        </div>
    </div>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;
    let audioUrl;
    let isRecording = false;
    let startTime;
    let timerInterval;
    let audioContext;
    let analyser;
    let microphone;
    let dataArray;
    let canvas;
    let canvasContext;
    
    // Initialize audio visualization
    function initializeVisualizer() {
        canvas = document.getElementById('visualizer');
        canvasContext = canvas.getContext('2d');
    }
    
    // Draw audio waveform
    function drawVisualizer() {
        if (!analyser || !isRecording) return;
        
        requestAnimationFrame(drawVisualizer);
        
        analyser.getByteFrequencyData(dataArray);
        
        canvasContext.fillStyle = '#f9f9f9';
        canvasContext.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = canvas.width / dataArray.length * 2.5;
        let barHeight;
        let x = 0;
        
        for (let i = 0; i < dataArray.length; i++) {
            barHeight = (dataArray[i] / 255) * canvas.height;
            
            const gradient = canvasContext.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
            gradient.addColorStop(0, '#4CAF50');
            gradient.addColorStop(1, '#2E86AB');
            
            canvasContext.fillStyle = gradient;
            canvasContext.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
    }
    
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 44100,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Setup audio context for visualization
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            microphone = audioContext.createMediaStreamSource(stream);
            microphone.connect(analyser);
            
            analyser.fftSize = 256;
            const bufferLength = analyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);
            
            initializeVisualizer();
            drawVisualizer();
            
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                audioUrl = URL.createObjectURL(audioBlob);
                
                const audioPlayback = document.getElementById('audioPlayback');
                audioPlayback.src = audioUrl;
                audioPlayback.style.display = 'block';
                
                document.getElementById('playBtn').disabled = false;
                document.getElementById('uploadSection').style.display = 'block';
                
                // Clean up
                stream.getTracks().forEach(track => track.stop());
                if (audioContext) {
                    audioContext.close();
                }
            };
            
            mediaRecorder.start();
            isRecording = true;
            startTime = Date.now();
            
            // Update UI
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('recordingStatus').innerHTML = '🔴 Recording in progress...';
            document.getElementById('recordingStatus').style.color = '#f44336';
            
            // Start timer
            timerInterval = setInterval(updateTimer, 100);
            
            // Auto-stop after 15 seconds
            setTimeout(() => {
                if (isRecording) {
                    stopRecording();
                }
            }, 15000);
            
        } catch (err) {
            document.getElementById('recordingStatus').innerHTML = '❌ Microphone access denied. Please allow microphone access.';
            document.getElementById('recordingStatus').style.color = '#f44336';
            console.error('Error accessing microphone:', err);
        }
    }
    
    function updateTimer() {
        if (isRecording && startTime) {
            const elapsed = (Date.now() - startTime) / 1000;
            document.getElementById('timer').innerHTML = `⏱️ ${elapsed.toFixed(1)}s`;
            
            if (elapsed >= 15) {
                document.getElementById('timer').innerHTML = `⏱️ 15.0s (Max reached)`;
            }
        }
    }
    
    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            clearInterval(timerInterval);
            
            // Update UI
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('recordingStatus').innerHTML = '✅ Recording completed!';
            document.getElementById('recordingStatus').style.color = '#4CAF50';
            
            // Clear visualizer
            const canvas = document.getElementById('visualizer');
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#f9f9f9';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#4CAF50';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Recording Complete ✅', canvas.width/2, canvas.height/2);
        }
    }
    
    function playRecording() {
        const audio = document.getElementById('audioPlayback');
        if (audio.paused) {
            audio.play();
            document.getElementById('playBtn').innerHTML = '⏸️ Pause';
        } else {
            audio.pause();
            document.getElementById('playBtn').innerHTML = '▶️ Play';
        }
    }
    
    // Reset play button when audio ends
    document.addEventListener('DOMContentLoaded', function() {
        const audio = document.getElementById('audioPlayback');
        audio.addEventListener('ended', function() {
            document.getElementById('playBtn').innerHTML = '▶️ Play';
        });
    });
    
    function uploadRecording() {
        if (audioBlob) {
            const reader = new FileReader();
            reader.onloadend = function() {
                const base64data = reader.result.split(',')[1];
                
                // Send to Streamlit
                window.parent.postMessage({
                    type: 'RECORDING_COMPLETE',
                    audioData: base64data,
                    mimeType: 'audio/wav'
                }, '*');
                
                document.getElementById('recordingStatus').innerHTML = '🎉 Recording uploaded successfully!';
                document.getElementById('recordingStatus').style.color = '#4CAF50';
                document.getElementById('uploadBtn').innerHTML = '✅ Uploaded!';
                document.getElementById('uploadBtn').disabled = true;
            };
            reader.readAsDataURL(audioBlob);
        }
    }
    
    // Initialize on load
    window.addEventListener('load', function() {
        initializeVisualizer();
    });
    </script>
    """
    
    # Display the recorder
    components.html(recorder_html, height=500)

def handle_recorded_audio(audio_data_base64):
    """Process recorded audio data"""
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(audio_data_base64)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data)
            temp_path = tmp_file.name
        
        # Store in session state
        st.session_state.voice_sample_path = temp_path
        st.session_state.recording_completed = True
        
        return temp_path
        
    except Exception as e:
        st.error(f"Error processing recorded audio: {e}")
        return None

def show_advanced_recorder():
    """Show the advanced voice recorder with visualization"""
    st.subheader("🎙️ Advanced Voice Recorder")
    
    # Create the recorder component
    create_audio_recorder()
    
    # Check for completed recording
    if st.session_state.get('recording_completed', False):
        st.success("🎉 Recording completed and ready for processing!")
        
        if st.button("📊 Analyze My Recording", type="primary"):
            if 'voice_sample_path' in st.session_state:
                # Process the recorded audio
                from ethical_voice_app import process_audio_sample
                process_audio_sample(st.session_state.voice_sample_path)
            else:
                st.error("❌ No recording found. Please record again.")
    
    # Instructions
    st.info("""
    **🎯 Recording Tips:**
    - Speak clearly and at normal volume
    - Record in a quiet environment
    - Keep recording between 5-15 seconds
    - Watch the visualizer to ensure audio is being captured
    - Listen to your recording before using it
    """)
    
    # Reset button
    if st.button("🔄 Reset Recorder"):
        if 'voice_sample_path' in st.session_state:
            try:
                if os.path.exists(st.session_state.voice_sample_path):
                    os.unlink(st.session_state.voice_sample_path)
            except:
                pass
            del st.session_state.voice_sample_path
        
        st.session_state.recording_completed = False
        st.rerun()
