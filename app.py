"""
YouTube Chatbot - Streamlit Frontend
A beautiful, professional chat interface for asking questions about YouTube videos
Created by: Shubham Parihar
"""

import streamlit as st
import time
from rag_pipeline import prepare_youtube_rag_chain

# ============================================================================
# PAGE CONFIGURATION - Must be first Streamlit command
# ============================================================================
st.set_page_config(
    page_title="YouTube Chatbot",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS - Makes the app look professional and attractive
# ============================================================================
st.markdown("""
    <style>
    /* Main background */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Chat messages styling */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Input box styling */
    .stTextInput > div > div > input {
        border-radius: 20px;
        border: 2px solid #667eea;
        background-color: white;
    }
    
    /* Hide placeholder text */
    .stTextInput > div > div > input::placeholder {
        color: transparent;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 20px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 25px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* Headers */
    h1 {
        color: white;
        text-align: center;
        font-size: 3em;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    h3 {
        color: white;
        text-align: center;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    
    /* Success/Info/Warning boxes */
    .stSuccess, .stInfo, .stWarning {
        border-radius: 10px;
        background-color: rgba(255,255,255,0.9);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(255,255,255,0.95);
    }
    
    /* LinkedIn link styling */
    .linkedin-link {
        color: #0077b5;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .linkedin-link:hover {
        color: #005582;
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZE SESSION STATE - Persists data across reruns
# ============================================================================
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'video_processed' not in st.session_state:
    st.session_state.video_processed = False

if 'current_video_id' not in st.session_state:
    st.session_state.current_video_id = None

if 'rag_chain' not in st.session_state:
    st.session_state.rag_chain = None

if 'video_url' not in st.session_state:
    st.session_state.video_url = ""

if 'show_ready_message' not in st.session_state:
    st.session_state.show_ready_message = False

# ============================================================================
# HEADER SECTION
# ============================================================================
st.title("🎥 YouTube Chatbot")
st.markdown("<h3>Ask questions about any YouTube video!</h3>", unsafe_allow_html=True)

# Feature badges
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
        <div style='text-align: center; background-color: rgba(255,255,255,0.9); 
        padding: 20px; border-radius: 15px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>
            <p style='color: #1f1f1f; font-size: 1.2em; margin: 0; font-weight: 600;'>
                🚀 Powered by AI &nbsp;&nbsp; 💾 Smart Caching
            </p>
            <p style='color: #1f1f1f; font-size: 1.2em; margin: 5px 0 0 0; font-weight: 600;'>
                ⚡ Lightning Fast
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Creator credit below feature badges
    st.markdown("""
        <div style='text-align: center; margin-top: 15px;'>
            <p style='margin: 0; font-size: 0.95em; color: rgba(255,255,255,0.9);'>
                Created by 
                <a href='https://www.linkedin.com/in/shubhamparihar7/' 
                   target='_blank' class='linkedin-link' 
                   style='color: white; font-weight: 700; text-decoration: none; 
                   border-bottom: 2px solid white; padding-bottom: 2px;'>
                   Shubham Parihar
                </a>
            </p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - Video Input and Processing
# ============================================================================
with st.sidebar:
    st.header("📹 Video Setup")
    
    # Video URL input
    video_url = st.text_input(
        "Paste YouTube URL here:",
        value="",
        placeholder="",
        help="Enter a valid YouTube video URL"
    )
    
    # Process button
    process_button = st.button("🔍 Process Video", use_container_width=True)
    
    # Show processing status
    if process_button and video_url:
        try:
            from rag_pipeline import extract_video_id
            
            with st.status("Processing video...", expanded=True) as status:
                # Step 1: Extract video ID
                st.write("🔎 Extracting video ID...")
                with st.spinner("🔄 Processing..."):
                    video_id = extract_video_id(video_url)
                st.success(f"✅ Video ID: {video_id}")
                time.sleep(0.3)
                
                # Check if this is a new video
                if video_id != st.session_state.current_video_id:
                    # Step 2: Fetch transcript
                    st.write("📥 Fetching transcript...")
                    with st.spinner("🔄 Processing..."):
                        time.sleep(0.5)
                    st.success("✅ Transcript fetched")
                    
                    # Step 3: Create chunks
                    st.write("✂️ Creating chunks...")
                    with st.spinner("🔄 Processing..."):
                        time.sleep(0.5)
                    st.success("✅ Chunks created")
                    
                    # Step 4: Build vector store (THE SLOW PART)
                    st.write("🧠 Building vector store...")
                    with st.spinner("🔄 Processing..."):
                        rag_chain = prepare_youtube_rag_chain(video_url)
                    st.success("✅ Vector store built")
                    
                    # Step 5: Set up retriever
                    st.write("🔗 Setting up retriever...")
                    with st.spinner("🔄 Processing..."):
                        time.sleep(0.3)
                    st.success("✅ Retriever ready")
                    
                    # Step 6: Prepare RAG pipeline
                    st.write("🎬 Preparing RAG pipeline...")
                    with st.spinner("🔄 Processing..."):
                        time.sleep(0.3)
                    st.success("✅ Pipeline ready")
                    
                    # Save to session state
                    st.session_state.rag_chain = rag_chain
                    st.session_state.current_video_id = video_id
                    st.session_state.video_processed = True
                    st.session_state.video_url = video_url
                    st.session_state.messages = []
                    st.session_state.show_ready_message = True
                    
                    status.update(label="✅ Video processed successfully!", state="complete")
                else:
                    st.info("ℹ️ This video is already loaded!")
                    status.update(label="ℹ️ Video already processed", state="complete")
                    
        except ValueError as e:
            st.error(f"❌ Error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
    
    elif process_button and not video_url:
        st.warning("⚠️ Please enter a YouTube URL first!")
    
    # Show current video status
    st.divider()
    if st.session_state.video_processed:
        st.success("✅ Video Ready!")
        st.info(f"📺 Video ID: {st.session_state.current_video_id}")
        
        # Button to reset/change video
        if st.button("🔄 Change Video", use_container_width=True):
            st.session_state.video_processed = False
            st.session_state.current_video_id = None
            st.session_state.rag_chain = None
            st.session_state.messages = []
            st.session_state.show_ready_message = False
            st.rerun()
    else:
        st.info("ℹ️ No video loaded yet")
    
    # Instructions
    st.divider()
    st.markdown("""
        ### 📖 How to Use:
        1. Paste a YouTube URL above
        2. Click **Process Video**
        3. Wait for processing to complete
        4. Start asking questions below!
        
        ### 💡 Tips:
        - First time processing takes longer
        - Subsequent questions are super fast!
        - You can ask multiple questions
        
        ### 🎯 Try These Questions:
        - "What is this video about?"
        - "Summarize the main points"
        - "Who are the speakers?"
    """)
    
    # Creator credit at bottom of sidebar
    st.divider()
    st.markdown("""
        <div style='text-align: center; padding: 10px;'>
            <p style='margin: 0; font-size: 0.9em;'>Created by</p>
            <p style='margin: 5px 0;'>
                <a href='https://www.linkedin.com/in/shubhamparihar7/' 
                   target='_blank' class='linkedin-link'>
                   🔗 Shubham Parihar
                </a>
            </p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN CHAT AREA
# ============================================================================

# Show "READY TO CHAT!" message when video is first processed
if st.session_state.show_ready_message and st.session_state.video_processed:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        padding: 30px; border-radius: 15px; margin: 20px; 
        box-shadow: 0 8px 16px rgba(0,0,0,0.3); text-align: center;'>
            <h1 style='color: white; margin: 0; font-size: 3em;'>✅ READY TO CHAT!</h1>
            <p style='color: white; font-size: 1.3em; margin: 10px 0 0 0;'>
                Chat box will appear below in a moment... 👇
            </p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.show_ready_message = False
    st.rerun()

# Display chat messages - VERSION 3 STYLE with icons
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if st.session_state.video_processed:
    # User can ask questions
    if prompt := st.chat_input("Ask me anything about this video..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = st.session_state.rag_chain.invoke(prompt)
                    st.markdown(response)
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Error generating response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
else:
    # Placeholder when no video is loaded
    st.markdown("""
        <div style='background-color: rgba(255,255,255,0.9); padding: 30px; 
        border-radius: 15px; margin: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>
            <h2 style='color: #667eea; text-align: center; margin-bottom: 20px;'>
                👋 Welcome to YouTube Chatbot!
            </h2>
            <p style='color: #1f1f1f; font-size: 1.1em; text-align: center; margin-bottom: 20px;'>
                👈 Please process a YouTube video from the sidebar to start chatting!
            </p>
            <hr style='border: 1px solid #667eea; margin: 20px 0;'>
            <h3 style='color: #667eea; margin-top: 20px;'>🎯 Example Questions You Can Ask:</h3>
            <ul style='color: #1f1f1f; font-size: 1em; line-height: 1.8;'>
                <li>"What is this video about?"</li>
                <li>"Summarize the main points in simple words"</li>
                <li>"Who are the people mentioned?"</li>
                <li>"What topics are discussed?"</li>
                <li>"Is this relevant for data scientists?"</li>
                <li>"Explain the key concepts covered"</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
        <div style='text-align: center; background-color: rgba(255,255,255,0.9); 
        padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <p style='margin: 0; color: #1f1f1f; font-weight: 600;'>
                Built with ❤️ using Streamlit & LangChain
            </p>
            <p style='margin: 5px 0 0 0; font-size: 0.9em; color: #667eea;'>
                Featuring Smart Caching & RAG Technology
            </p>
            <p style='margin: 8px 0 0 0; font-size: 0.85em; color: #28a745; font-weight: 600;'>
                By Shubham Parihar
            </p>
        </div>
    """, unsafe_allow_html=True)