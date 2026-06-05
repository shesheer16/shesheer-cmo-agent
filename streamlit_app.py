"""
streamlit_app.py — Root-level entry point for Streamlit Community Cloud.
Streamlit Cloud looks for this file at the repo root.
Sets PYTHONPATH so src/ imports work correctly.
"""
import sys
import os

# Make sure src/ is importable from repo root
sys.path.insert(0, os.path.dirname(__file__))

# Password gate — protects private strategic tool from public access
import streamlit as st

def check_password():
    password = st.secrets.get("APP_PASSWORD", None)
    if password is None:
        # No password configured in Streamlit secrets → allow access
        return True
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.title("🔐 Shesheer CMO Agent")
    entered = st.text_input("Enter access password:", type="password", key="pw_input")
    if st.button("Enter"):
        if entered == password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if check_password():
    # Import and run the actual Streamlit app
    from src.interface.streamlit_app import main as run_app
    run_app()
