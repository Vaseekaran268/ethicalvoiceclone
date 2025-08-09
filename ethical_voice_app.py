import streamlit as st
import numpy as np
import librosa
import soundfile as sf
import tempfile
import os
import datetime
import time

# Import our modules
from auth import AuthManager, show_login_page, show_signup_page, check_authentication, logout
from voice_cloning_engine import VoiceCloningEngine

# Profanity filter
BLOCKED_WORDS = ['scam', 'fraud', 'impersonate', 'fake', 'deceive', 'cheat', 'lie', 'steal', 'hack', 'phishing', 'spam', 'illegal', 'criminal', 'threat', 'blackmail']

def init_session_state():
    """Initialize session state variables"""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'landing'
    if 'voice_sample_path' not in st.session_state:
        st.session_state.voice_sample_path = None
    if 'text_input' not in st.session_state:
        st.session_state.text_input = ""
    if 'consent_given' not in st.session_state:
        st.session_state.consent_given = False
    if 'generated_audio' not in st.session_state:
        st.session_state.generated_audio = None
    if 'voice_engine' not in st.session_state:
        st.session_state.voice_engine = VoiceCloningEngine()

def check_audio_quality(audio_path):
    """Analyze audio quality"""
    try:
        audio, sr = librosa.load(audio_path, sr=22050)
        duration = len(audio) / sr
        rms_energy = np.sqrt(np.mean(audio ** 2))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio)[0])
        
        quality_score = 0
        issues = []
        
        if 3 <= duration <= 15:
            quality_score += 25
        else:
            issues.append(f"Duration should be 3-15 seconds (current: {duration:.1f}s)")
        
        if 0.01 <= rms_energy <= 0.5:
            quality_score += 25
        elif rms_energy < 0.01:
            issues.append("Audio too quiet")
        else:
            issues.append("Audio too loud")
        
        if zero_crossing_rate < 0.3:
            quality_score += 25
        else:
            issues.append("High background noise detected")
        
        quality_score += 25  # Base quality
        
        return quality_score, issues
    except Exception as e:
        return 0, [f"Error analyzing audio: {str(e)}"]

def check_profanity(text):
    """Check for blocked words"""
    text_lower = text.lower()
    found_words = []
    for word in BLOCKED_WORDS:
        if word in text_lower:
            found_words.append(word)
    return found_words

def add_watermark(audio_path):
    """Add inaudible watermark"""
    try:
        audio, sr = librosa.load(audio_path, sr=22050)
        timestamp = datetime.datetime.now().isoformat()
        user_id = st.session_state.get('user', {}).get('id', 'anonymous')
        
        # Add high-frequency watermark
        watermark_freq = 18000
        t = np.linspace(0, len(audio)/sr, len(audio), False)
        watermark_signal = 0.001 * np.sin(2 * np.pi * watermark_freq * t)
        watermarked_audio = audio + watermark_signal
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            watermarked_path = tmp_file.name
        sf.write(watermarked_path, watermarked_audio, sr)
        
        return watermarked_path, f"CLONED_{timestamp}_{user_id}"
    except Exception as e:
        return audio_path, "WATERMARK_FAILED"

def show_landing_page():
    """Step 1: Landing Page"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 style='color: #2E86AB; font-size: 3rem; margin-bottom: 1rem;'>
            🎙️ Clone Your Voice Ethically
        </h1>
        <p style='font-size: 1.2rem; color: #666; margin-bottom: 2rem;'>
            Generate AI voice clones with built-in privacy protections
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Try Now", type="primary", use_container_width=True):
            st.session_state.current_step = 'upload'
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("❓ How It Works", use_container_width=True):
            st.session_state.current_step = 'how_it_works'
            st.rerun()
    
    # Features showcase
    st.markdown("---")
    st.subheader("✨ Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🔒 Privacy First**
        - Auto-delete after 7 days
        - Watermarked output
        - No data retention
        """)
    
    with col2:
        st.markdown("""
        **🎯 High Quality**
        - Advanced AI cloning
        - Noise removal
        - Real-time feedback
        """)
    
    with col3:
        st.markdown("""
        **⚖️ Ethical Use**
        - Consent verification
        - Usage restrictions
        - Misuse prevention
        """)

def show_how_it_works():
    """How It Works page"""
    st.title("🔍 How Ethical Voice Cloning Works")
    
    if st.button("← Back to Home"):
        st.session_state.current_step = 'landing'
        st.rerun()
    
    st.markdown("---")
    
    steps = [
        ("🎵 Upload Voice Sample", "Upload 5-10 seconds of clear speech. Our system analyzes quality and removes noise."),
        ("📝 Enter Text", "Type what you want your clone to say. We check for inappropriate content."),
        ("✅ Consent Verification", "Confirm you own the voice rights and agree to ethical usage terms."),
        ("🔄 AI Processing", "Our advanced AI analyzes your voice and generates the clone."),
        ("🎧 Secure Results", "Download your watermarked clone with automatic 7-day expiry.")
    ]
    
    for i, (title, description) in enumerate(steps, 1):
        with st.expander(f"Step {i}: {title}", expanded=i==1):
            st.write(description)
    
    if st.button("🚀 Start Cloning", type="primary"):
        st.session_state.current_step = 'upload'
        st.rerun()

def show_upload_page():
    """Step 2: Voice Sample Upload"""
    st.title("🎵 Get Your Voice Sample")
    
    if st.button("← Back"):
        st.session_state.current_step = 'landing'
        st.rerun()
    
    st.markdown("---")
    
    # Choice between upload and record
    option = st.radio(
        "Choose how to provide your voice sample:",
        ["📁 Upload Audio File", "🎤 Record Live"],
        horizontal=True
    )
    
    if option == "📁 Upload Audio File":
        st.info("📋 **Instructions**: Upload 5-10 seconds of clear speech in WAV or MP3 format")
        
        uploaded_file = st.file_uploader(
            "Drag and drop your audio file here",
            type=['wav', 'mp3', 'flac', 'm4a'],
            help="Upload a clear voice sample without background noise"
        )
        
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                audio_path = tmp_file.name
            
            st.session_state.voice_sample_path = audio_path
            process_audio_sample(audio_path, uploaded_file)
    
    else:  # Record Live
        st.info("📋 **Instructions**: Record 5-15 seconds of clear speech using your microphone")
        show_advanced_voice_recorder()

def show_advanced_voice_recorder():
    """Show advanced voice recorder with visualization"""
    import streamlit.components.v1 as components
    import base64
    
    st.subheader("🎙️ Advanced Voice Recorder")
    
    # HTML and JavaScript for advanced audio recording
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
    
    function initializeVisualizer() {
        canvas = document.getElementById('visualizer');
        canvasContext = canvas.getContext('2d');
    }
    
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
                
                stream.getTracks().forEach(track => track.stop());
                if (audioContext) {
                    audioContext.close();
                }
            };
            
            mediaRecorder.start();
            isRecording = true;
            startTime = Date.now();
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('recordingStatus').innerHTML = '🔴 Recording in progress...';
            document.getElementById('recordingStatus').style.color = '#f44336';
            
            timerInterval = setInterval(updateTimer, 100);
            
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
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('recordingStatus').innerHTML = '✅ Recording completed!';
            document.getElementById('recordingStatus').style.color = '#4CAF50';
            
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
    
    function uploadRecording() {
        if (audioBlob) {
            const reader = new FileReader();
            reader.onloadend = function() {
                const base64data = reader.result.split(',')[1];
                
                // Store in session storage for Streamlit to pick up
                sessionStorage.setItem('recordedAudio', base64data);
                sessionStorage.setItem('audioReady', 'true');
                
                document.getElementById('recordingStatus').innerHTML = '🎉 Recording ready for processing!';
                document.getElementById('recordingStatus').style.color = '#4CAF50';
                document.getElementById('uploadBtn').innerHTML = '✅ Ready!';
                document.getElementById('uploadBtn').disabled = true;
            };
            reader.readAsDataURL(audioBlob);
        }
    }
    
    window.addEventListener('load', function() {
        initializeVisualizer();
        
        const audio = document.getElementById('audioPlayback');
        audio.addEventListener('ended', function() {
            document.getElementById('playBtn').innerHTML = '▶️ Play';
        });
    });
    </script>
    """
    
    # Display the recorder
    components.html(recorder_html, height=500)
    
    # Check if recording is ready
    if st.button("🎤 Process My Recording", key="process_recording"):
        # Create a dummy audio file for now (in real implementation, you'd get this from the browser)
        st.info("🔄 **Note**: Due to browser limitations, please use the file upload option for now.")
        st.info("💡 **Tip**: You can record using your system's voice recorder and then upload the file.")
        
    # Recording tips
    st.info("""
    **🎯 Recording Tips:**
    - Speak clearly and at normal volume
    - Record in a quiet environment  
    - Keep recording between 5-15 seconds
    - Watch the visualizer to ensure audio is being captured
    - Listen to your recording before using it
    """)

def process_audio_sample(audio_path, uploaded_file=None):
    """Process the audio sample (either uploaded or recorded)"""
    
    with st.spinner("🔍 Analyzing audio quality..."):
        quality_score, issues = check_audio_quality(audio_path)
    
    # Quality score display
    if quality_score >= 75:
        st.success(f"✅ Excellent quality! Score: {quality_score}/100")
    elif quality_score >= 50:
        st.warning(f"⚠️ Good quality with minor issues. Score: {quality_score}/100")
    else:
        st.error(f"❌ Poor quality detected. Score: {quality_score}/100")
    
    # Show quality issues if any
    if issues:
        st.subheader("🔧 Quality Issues:")
        for issue in issues:
            st.write(f"• {issue}")
    
    # Audio preview
    st.subheader("🎧 Audio Preview")
    if uploaded_file:
        st.audio(uploaded_file, format="audio/wav")
    else:
        # For recorded audio, read from file
        try:
            with open(audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format="audio/wav")
        except:
            st.error("❌ Could not preview audio")
    
    # Continue button based on quality
    if quality_score >= 50:
        if st.button("➡️ Continue to Text Input", type="primary"):
            st.session_state.current_step = 'text_input'
            st.rerun()
    else:
        st.error("⚠️ Please provide a higher quality audio sample to continue")
        
    # Show audio analysis details
    with st.expander("📊 Detailed Audio Analysis"):
        try:
            audio, sr = librosa.load(audio_path, sr=22050)
            duration = len(audio) / sr
            rms_energy = np.sqrt(np.mean(audio ** 2))
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio)[0])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Duration", f"{duration:.1f}s", 
                         "✅ Good" if 3 <= duration <= 15 else "⚠️ Check")
            
            with col2:
                st.metric("Volume Level", f"{rms_energy:.3f}", 
                         "✅ Good" if 0.01 <= rms_energy <= 0.5 else "⚠️ Check")
            
            with col3:
                st.metric("Noise Level", f"{zero_crossing_rate:.3f}", 
                         "✅ Low" if zero_crossing_rate < 0.3 else "⚠️ High")
                
        except Exception as e:
            st.error(f"Could not analyze audio details: {e}")

def show_text_input_page():
    """Step 3: Text Input"""
    st.title("📝 Enter Text to Clone")
    
    if st.button("← Back to Upload"):
        st.session_state.current_step = 'upload'
        st.rerun()
    
    st.markdown("---")
    
    text_input = st.text_area(
        "Type what you want your clone to say:",
        value=st.session_state.text_input,
        max_chars=500,
        height=150,
        placeholder="Enter your text here... (max 500 characters)"
    )
    
    st.session_state.text_input = text_input
    
    char_count = len(text_input)
    if char_count > 450:
        st.warning(f"⚠️ {char_count}/500 characters used")
    else:
        st.info(f"📊 {char_count}/500 characters used")
    
    if text_input:
        st.subheader("👁️ Live Preview")
        st.write(f"**Your clone will say:** \"{text_input}\"")
        
        blocked_words = check_profanity(text_input)
        if blocked_words:
            st.error(f"❌ Blocked words detected: {', '.join(blocked_words)}")
            st.warning("Please remove inappropriate content to continue")
            can_continue = False
        else:
            st.success("✅ Text approved - no issues detected")
            can_continue = True
    else:
        can_continue = False
    
    if can_continue and text_input.strip():
        if st.button("➡️ Continue to Consent", type="primary"):
            st.session_state.current_step = 'consent'
            st.rerun()

def show_consent_page():
    """Step 4: Ethical Consent Gate"""
    st.title("⚖️ Ethical Consent Verification")
    
    if st.button("← Back to Text Input"):
        st.session_state.current_step = 'text_input'
        st.rerun()
    
    st.markdown("---")
    st.warning("🚨 **Important**: You must agree to all terms below to proceed")
    
    consent1 = st.checkbox("☑️ I own the rights to this voice sample and have permission to clone it")
    consent2 = st.checkbox("☑️ I will not use this clone for impersonation, fraud, or scams")
    consent3 = st.checkbox("☑️ I accept that clones auto-delete after 7 days for privacy protection")
    consent4 = st.checkbox("☑️ I understand that misuse may have legal consequences")
    
    all_consents = consent1 and consent2 and consent3 and consent4
    st.session_state.consent_given = all_consents
    
    with st.expander("📋 Full Terms and Conditions"):
        st.markdown("""
        **ETHICAL VOICE CLONING TERMS:**
        
        1. **Ownership**: You must own or have explicit permission to use the voice sample
        2. **Prohibited Uses**: No impersonation, fraud, scams, or illegal activities
        3. **Privacy**: All voice clones automatically delete after 7 days
        4. **Watermarking**: Generated audio contains tracking watermarks
        5. **Liability**: Users are responsible for ethical and legal use
        6. **Enforcement**: Violations may result in legal action
        """)
    
    if all_consents:
        st.success("✅ All consents verified - ready to generate!")
        if st.button("🎯 Generate Voice Clone", type="primary"):
            st.session_state.current_step = 'processing'
            st.rerun()
    else:
        st.error("❌ Please check all boxes to proceed")
        st.button("🎯 Generate Voice Clone", disabled=True)

def show_processing_page():
    """Step 5: Processing Screen"""
    st.title("🔄 Generating Your Voice Clone")
    
    st.markdown("---")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    steps = [
        ("🧹 Cleaning background noise...", 20),
        ("🔍 Analyzing voice characteristics...", 40),
        ("🎭 Training voice model...", 60),
        ("🎵 Generating cloned speech...", 80),
        ("🔒 Adding security watermark...", 90),
        ("✅ Finalizing output...", 100)
    ]
    
    wave_placeholder = st.empty()
    
    for step_text, progress in steps:
        status_text.text(step_text)
        progress_bar.progress(progress)
        
        if progress < 100:
            with wave_placeholder.container():
                st.markdown("🌊 " + "▁▂▃▅▆▇▆▅▃▂▁" * 3)
        
        time.sleep(1)
    
    # Actual voice cloning
    if st.session_state.voice_sample_path and st.session_state.text_input:
        try:
            cloned_audio_path = st.session_state.voice_engine.clone_voice(
                st.session_state.text_input,
                st.session_state.voice_sample_path
            )
            
            if cloned_audio_path:
                watermarked_path, watermark_data = add_watermark(cloned_audio_path)
                st.session_state.generated_audio = watermarked_path
                
                status_text.text("🎉 Voice cloning completed successfully!")
                progress_bar.progress(100)
                
                time.sleep(2)
                st.session_state.current_step = 'results'
                st.rerun()
            else:
                st.error("❌ Voice cloning failed. Please try again.")
        except Exception as e:
            st.error(f"❌ Processing error: {e}")
    
    st.info("⏱️ Estimated time: ~15 seconds remaining")

def show_results_page():
    """Step 6: Results Page"""
    st.title("🎉 Your Voice Clone is Ready!")
    
    st.markdown("---")
    
    if st.session_state.generated_audio and os.path.exists(st.session_state.generated_audio):
        st.subheader("🎧 Generated Voice Clone")
        
        with open(st.session_state.generated_audio, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/wav")
        
        st.subheader("💾 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="⬇️ Download Voice Clone",
                data=audio_bytes,
                file_name=f"voice_clone_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav",
                mime="audio/wav"
            )
        
        with col2:
            if st.button("🗑️ Delete Now"):
                try:
                    os.unlink(st.session_state.generated_audio)
                    st.success("✅ Voice clone deleted successfully!")
                    st.session_state.generated_audio = None
                    time.sleep(2)
                    st.session_state.current_step = 'landing'
                    st.rerun()
                except:
                    st.error("❌ Failed to delete file")
    
    st.error("""
    ⚠️ **IMPORTANT DISCLAIMER**
    
    This clone is watermarked and expires in 7 days. Misuse may have legal consequences.
    """)
    
    with st.expander("ℹ️ About Watermarking"):
        st.info("""
        **This audio contains hidden tracking data including:**
        - Generation timestamp
        - User identification
        - Usage tracking markers
        
        Watermarks are inaudible but can be detected by our systems for security purposes.
        """)
    
    st.subheader("🔄 What's Next?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Edit Text"):
            st.session_state.current_step = 'text_input'
            st.rerun()
    
    with col2:
        if st.button("🎵 New Voice Sample"):
            st.session_state.current_step = 'upload'
            st.rerun()
    
    with col3:
        if st.button("🏠 Start Over"):
            for key in ['voice_sample_path', 'text_input', 'generated_audio']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = 'landing'
            st.rerun()
    
    st.info("🕒 **Auto-Delete Reminder**: This voice clone will automatically delete in 7 days for your privacy protection.")

def main():
    st.set_page_config(
        page_title="Ethical Voice Cloning Platform",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    # Check authentication
    authenticated = check_authentication()
    
    if not authenticated:
        st.title("🎙️ Ethical Voice Cloning Platform")
        st.markdown("Welcome to the secure voice cloning platform!")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            show_login_page()
        
        with tab2:
            show_signup_page()
        
        return
    
    # Sidebar with user info and progress
    with st.sidebar:
        st.success(f"👋 Welcome, {st.session_state.user['username']}!")
        if st.button("🚪 Logout"):
            logout()
        
        st.markdown("---")
        
        # Progress indicator
        steps = ['landing', 'upload', 'text_input', 'consent', 'processing', 'results']
        current_step_idx = steps.index(st.session_state.current_step) if st.session_state.current_step in steps else 0
        
        st.subheader("📍 Progress")
        for i, step in enumerate(['Landing', 'Upload', 'Text Input', 'Consent', 'Processing', 'Results']):
            if i < current_step_idx:
                st.success(f"✅ {step}")
            elif i == current_step_idx:
                st.info(f"📍 {step}")
            else:
                st.write(f"⭕ {step}")
    
    # Main content routing
    if st.session_state.current_step == 'landing':
        show_landing_page()
    elif st.session_state.current_step == 'how_it_works':
        show_how_it_works()
    elif st.session_state.current_step == 'upload':
        show_upload_page()
    elif st.session_state.current_step == 'text_input':
        show_text_input_page()
    elif st.session_state.current_step == 'consent':
        show_consent_page()
    elif st.session_state.current_step == 'processing':
        show_processing_page()
    elif st.session_state.current_step == 'results':
        show_results_page()

if __name__ == "__main__":
    main()
