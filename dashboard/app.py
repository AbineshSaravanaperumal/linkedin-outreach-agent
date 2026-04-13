import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# Adjust path so agent module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.scraper import get_or_create_profile, save_message, get_message_history, create_tables
from agent.prompt_builder import generate_message
from agent.voice_calibrator import DEFAULT_SAMPLES

# Page Configuration
st.set_page_config(
    page_title="OutreachAI — LinkedIn Agent",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .stApp {
        background: #08090d;
        color: #e8eaf0;
    }
    .stButton > button {
        background: #4f8ef7 !important;
        color: #08090d !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background: #3b7cf6 !important;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #4f8ef7;
    }
    .profile-card {
        background: #0f1117;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #1e222d;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'voice_samples' not in st.session_state:
    st.session_state.voice_samples = DEFAULT_SAMPLES.copy()

if 'messages_count' not in st.session_state:
    st.session_state.messages_count = 0

# Run table creation at startup
create_tables()

# Sidebar Navigation
with st.sidebar:
    st.markdown("## ✉️ OutreachAI")
    st.caption("LinkedIn Message Agent")
    st.divider()
    
    page = st.radio(
        "Navigation",
        options=["Generate Message", "Batch Mode", "Voice Calibration", "Message History", "Settings"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.metric("Total Generated", st.session_state.messages_count)
    
    st.sidebar.markdown(f"""
    <div style='position: fixed; bottom: 20px;'>
        <p style='color: #666; font-size: 0.8em;'>© {datetime.now().year} OutreachAI</p>
    </div>
    """, unsafe_allow_html=True)

# --- PAGE: Generate Message ---
if page == "Generate Message":
    st.title("✉️ Generate Outreach")
    st.caption("Personalized messages for LinkedIn leads.")
    
    col_in, col_out = st.columns([1, 1], gap="large")
    
    with col_in:
        st.subheader("Input")
        url = st.text_input("LinkedIn Profile URL", placeholder="https://linkedin.com/in/danmartell")
        
        profile = None
        if url and "linkedin.com/in/" in url:
            with st.spinner("Looking up profile..."):
                scraped = get_or_create_profile(url)
                if scraped:
                    with st.expander(f"👤 Profile Context (Editable)", expanded=True):
                        st.caption("No API key? You can manually paste details from their profile below:")
                        p_name = st.text_input("Name", value=scraped['name'])
                        p_role = st.text_input("Role", value=scraped['current_role'])
                        p_comp = st.text_input("Company", value=scraped['company'])
                        p_head = st.text_input("Headline", value=scraped['headline'])
                        p_post = st.text_area("Recent Activity", value=scraped['recent_post'], height=100)
                        
                        profile = {
                            "id": scraped['id'],
                            "name": p_name,
                            "current_role": p_role,
                            "company": p_comp,
                            "headline": p_head,
                            "recent_post": p_post
                        }
        
        bio = st.text_area("Your Bio / Offer", height=90, placeholder="e.g. I help B2B founders scale using AI...")
        ctx = st.text_area("Why reaching out?", height=70, placeholder="e.g. Saw their recent post on delegation...")
        tone = st.select_slider("Select Tone", options=["Casual", "Professional", "Bold"])
        
        gen_btn = st.button("🚀 Generate Message", disabled=not (url and bio and profile))
        
        if gen_btn and profile:
            with st.spinner("Crafting your message..."):
                result = generate_message(profile, bio, ctx, tone, st.session_state.voice_samples)
                st.session_state.last_msg = result
                st.session_state.last_profile = profile
                st.session_state.last_tone = tone
                st.session_state.messages_count += 1
                st.rerun()

    with col_out:
        st.subheader("Output")
        if 'last_msg' in st.session_state:
            msg = st.session_state.last_msg
            words = len(msg.split())
            
            c1, c2 = st.columns(2)
            c1.success(f"Tone: {st.session_state.last_tone}")
            c2.info(f"{words} words")
            
            edited_msg = st.text_area("Message Preview", msg, height=220, key="msg_area")
            
            sc1, sc2 = st.columns(2)
            if sc1.button("💾 Save to History"):
                save_message(st.session_state.last_profile["id"], bio, st.session_state.last_tone, edited_msg)
                st.success("Saved!")
                
            if sc2.button("🔄 Regenerate"):
                # Clear last message to force a new generation on rerun
                del st.session_state.last_msg
                st.rerun()
                
            st.code(edited_msg, language=None)
            st.caption("Copy the message above ↑")
        else:
            st.info("Fill in the URL and bio, then click Generate to start.")

# --- PAGE: Batch Mode ---
elif page == "Batch Mode":
    st.title("🚀 Batch Mode")
    st.caption("Process up to 10 LinkedIn profiles at once.")
    
    urls_raw = st.text_area("LinkedIn URLs (one per line)", placeholder="https://linkedin.com/in/user1\nhttps://linkedin.com/in/user2", height=140)
    batch_bio = st.text_area("Your Bio", height=80)
    batch_tone = st.select_slider("Batch Tone", ["Casual", "Professional", "Bold"])
    ctx_batch = st.text_input("Context for all (optional)")
    
    if st.button("🚀 Run Batch"):
        if not urls_raw or not batch_bio:
            st.error("Please provide URLs and your Bio.")
        else:
            urls = [u.strip() for u in urls_raw.split("\n") if "linkedin.com/in/" in u][:10]
            if not urls:
                st.error("No valid LinkedIn URLs found.")
            else:
                results = []
                progress_bar = st.progress(0)
                status = st.empty()
                
                for i, url in enumerate(urls):
                    status.text(f"Processing ({i+1}/{len(urls)}): {url}")
                    profile = get_or_create_profile(url)
                    msg = generate_message(profile, batch_bio, ctx_batch, batch_tone, st.session_state.voice_samples)
                    
                    results.append({
                        "Name": profile['name'],
                        "Tone": batch_tone,
                        "Message": msg
                    })
                    
                    st.session_state.messages_count += 1
                    progress_bar.progress((i + 1) / len(urls))
                
                status.success(f"Processed {len(urls)} profiles!")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Results", csv, f"batch_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

# --- PAGE: Voice Calibration ---
elif page == "Voice Calibration":
    st.title("🎚️ Voice Calibration")
    st.caption("Fine-tune the AI to match your writing style.")
    st.info("The AI studies these samples to replicate your specific sentence structure, punctuation, and style.")
    
    new_samples = []
    for i, sample in enumerate(st.session_state.voice_samples):
        val = st.text_area(f"Sample {i+1}", value=sample, height=100, key=f"voice_{i}")
        new_samples.append(val)
        
    c1, c2 = st.columns(2)
    if c1.button("➕ Add Sample"):
        st.session_state.voice_samples.append("")
        st.rerun()
        
    if c2.button("💾 Save Samples"):
        st.session_state.voice_samples = [s for s in new_samples if s.strip()]
        st.success("Samples saved! These will be used for future generations.")

# --- PAGE: Message History ---
elif page == "Message History":
    st.title("📜 Message History")
    rows = get_message_history(50)
    
    if rows:
        df = pd.DataFrame(rows, columns=["Name", "Current Role", "Tone", "Output", "Created At"])
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download History", csv, "outreach_history.csv", "text/csv")
    else:
        st.info("No messages saved yet.")

# --- PAGE: Settings ---
elif page == "Settings":
    st.title("⚙️ Settings")
    
    st.subheader("Google API Key")
    st.info("Ensure your `.env` file contains your Google API key or set it in Streamlit Secrets.")
    st.code("GOOGLE_API_KEY=your-gemini-key-here")
    
    st.subheader("ProxyCurl API Key")
    st.info("ProxyCurl is used for real-time profile scraping. Without it, we fallback to URL parsing.")
    st.code("PROXYCURL_API_KEY=your-proxycurl-key")
    
    st.subheader("Project Structure")
    st.code("""
D:\\linkedin-outreach-agent\\
├── agent\\
│   ├── scraper.py
│   ├── prompt_builder.py
│   └── voice_calibrator.py
├── dashboard\\
│   └── app.py
├── data\\
│   └── messages.db
└── requirements.txt
    """)

# Footer
st.divider()
st.caption(f"OutreachAI · Built by Abinesh · {datetime.now().strftime('%B %Y')}")
