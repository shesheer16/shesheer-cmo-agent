import streamlit as st
import asyncio
import os
import tempfile
from pathlib import Path
import google.api_core.exceptions as google_exceptions

from src.core.orchestrator import CMOAgent
from src.memory.context_manager import context_manager
from src.utils.logger import logger
from scripts.ingest_pdf_batch import run_batch as ingest_pdf_batch

st.set_page_config(page_title="CMO Agent", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# Initialize agent globally
@st.cache_resource
def get_agent():
    return CMOAgent()

agent = get_agent()

def handle_pdf_upload(uploaded_file):
    pdf_dir = Path("data/knowledge_base/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = pdf_dir / uploaded_file.name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        ingest_pdf_batch()
        st.toast("PDF ingested successfully!", icon="✅")
    except Exception as e:
        logger.error(f"PDF ingestion error: {e}")
        st.toast("Failed to ingest PDF.", icon="❌")

def main():
    st.title("Indian CMO Agent 📈")
    
    # Ensure state tracking
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Sidebar
    with st.sidebar:
        st.header("🧠 Startup Context")
        context_summary = context_manager.get_context_summary()
        st.info(context_summary)
        
        st.header("🗂️ Knowledge Base")
        uploaded_pdf = st.file_uploader("Upload PDF report", type=["pdf"])
        if uploaded_pdf is not None:
            with st.spinner("Ingesting PDF..."):
                handle_pdf_upload(uploaded_pdf)
                
        st.header("💰 Cost Tracker")
        st.write("Tracking via DB in progress")
        
    # Main chat
    # Display recent history from DB as initialization if empty
    if not st.session_state.messages:
        recent_history = context_manager.get_recent_conversations(5)
        for turn in recent_history:
            if "Founder:" in turn and "CMO:" in turn:
                u, c = turn.split("CMO:", 1)
                st.session_state.messages.append({"role": "user", "content": u.replace("Founder: ", "").strip()})
                st.session_state.messages.append({"role": "assistant", "content": c.strip()})
                
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    user_input = st.chat_input("Ask the CMO a strategic question...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Execute orchestrator
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    response = loop.run_until_complete(agent.respond(user_input))
                    
                    st.markdown(response.response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response.response_text})
                    
                    with st.expander(f"💡 Sources ({len(response.sources_used)})"):
                        for s in response.sources_used:
                            st.write(f"- {s}")
                            
                except google_exceptions.ResourceExhausted:
                    st.error("API limit hit, retry in 30 seconds")
                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    st.error("Processing error. Try again.")

if __name__ == "__main__":
    main()
