import streamlit as st
import time
import datetime

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
    """How It Works explanation page"""
    st.title("🔍 How Ethical Voice Cloning Works")
    
    if st.button("← Back to Home"):
        st.session_state.current_step = 'landing'
        st.rerun()
    
    st.markdown("---")
    
    # Process steps
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
    
    st.markdown("---")
    
    # Ethics section
    st.subheader("⚖️ Our Ethical Commitments")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Privacy Protection:**
        - All clones auto-delete after 7 days
        - No permanent storage of voice data
        - Watermarked output for tracking
        - User consent required for processing
        """)
    
    with col2:
        st.markdown("""
        **Misuse Prevention:**
        - Content filtering for harmful text
        - Usage agreement enforcement
        - Legal consequences for misuse
        - Transparent watermarking system
        """)
    
    if st.button("🚀 Start Cloning", type="primary"):
        st.session_state.current_step = 'upload'
        st.rerun()

def show_consent_page():
    """Step 4: Ethical Consent Gate"""
    st.title("⚖️ Ethical Consent Verification")
    
    if st.button("← Back to Text Input"):
        st.session_state.current_step = 'text_input'
        st.rerun()
    
    st.markdown("---")
    
    st.warning("🚨 **Important**: You must agree to all terms below to proceed")
    
    # Consent checkboxes
    consent1 = st.checkbox("☑️ I own the rights to this voice sample and have permission to clone it")
    consent2 = st.checkbox("☑️ I will not use this clone for impersonation, fraud, or scams")
    consent3 = st.checkbox("☑️ I accept that clones auto-delete after 7 days for privacy protection")
    consent4 = st.checkbox("☑️ I understand that misuse may have legal consequences")
    
    all_consents = consent1 and consent2 and consent3 and consent4
    st.session_state.consent_given = all_consents
    
    # Legal disclaimer
    with st.expander("📋 Full Terms and Conditions"):
        st.markdown("""
        **ETHICAL VOICE CLONING TERMS:**
        
        1. **Ownership**: You must own or have explicit permission to use the voice sample
        2. **Prohibited Uses**: No impersonation, fraud, scams, or illegal activities
        3. **Privacy**: All voice clones automatically delete after 7 days
        4. **Watermarking**: Generated audio contains tracking watermarks
        5. **Liability**: Users are responsible for ethical and legal use
        6. **Enforcement**: Violations may result in legal action
        
        By proceeding, you agree to these terms and confirm ethical usage.
        """)
    
    # Generate button (only enabled when all consents given)
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
    
    # Progress animation
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Processing steps
    steps = [
        ("🧹 Cleaning background noise...", 20),
        ("🔍 Analyzing voice characteristics...", 40),
        ("🎭 Training voice model...", 60),
        ("🎵 Generating cloned speech...", 80),
        ("🔒 Adding security watermark...", 90),
        ("✅ Finalizing output...", 100)
    ]
    
    # Animated soundwave (placeholder)
    wave_placeholder = st.empty()
    
    # Simulate processing
    for step_text, progress in steps:
        status_text.text(step_text)
        progress_bar.progress(progress)
        
        # Show animated wave
        if progress < 100:
            with wave_placeholder.container():
                st.markdown("🌊 " + "▁▂▃▅▆▇▆▅▃▂▁" * 3)
        
        time.sleep(1)  # Simulate processing time
    
    # Estimated time
    st.info("⏱️ Estimated time: ~15 seconds remaining")
    
    return True  # Indicates processing complete

def show_results_page(generated_audio_path):
    """Step 6: Results Page"""
    st.title("🎉 Your Voice Clone is Ready!")
    
    st.markdown("---")
    
    if generated_audio_path and os.path.exists(generated_audio_path):
        # Audio player
        st.subheader("🎧 Generated Voice Clone")
        
        with open(generated_audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/wav")
        
        # Download button with warning
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
                    os.unlink(generated_audio_path)
                    st.success("✅ Voice clone deleted successfully!")
                    st.session_state.generated_audio = None
                    time.sleep(2)
                    st.session_state.current_step = 'landing'
                    st.rerun()
                except:
                    st.error("❌ Failed to delete file")
    
    # Disclaimer banner
    st.error("""
    ⚠️ **IMPORTANT DISCLAIMER**
    
    This clone is watermarked and expires in 7 days. Misuse may have legal consequences.
    """)
    
    # Watermark info
    with st.expander("ℹ️ About Watermarking"):
        st.info("""
        **This audio contains hidden tracking data including:**
        - Generation timestamp
        - User identification
        - Usage tracking markers
        
        Watermarks are inaudible but can be detected by our systems for security purposes.
        """)
    
    # Options
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
            # Clear session state
            for key in ['voice_sample', 'voice_sample_path', 'text_input', 'generated_audio']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = 'landing'
            st.rerun()
    
    # Auto-delete reminder
    st.info("🕒 **Auto-Delete Reminder**: This voice clone will automatically delete in 7 days for your privacy protection.")
