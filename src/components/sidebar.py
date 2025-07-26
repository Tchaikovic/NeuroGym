"""
Sidebar component - handles navigation and user information
"""
import streamlit as st
from ..database import save_chat_history, serialize_chat_history
from ..config import DEFAULT_SYSTEM_PROMPT

def show_sidebar():
    """Display sidebar with user info and navigation"""
    if st.session_state.user is not None:
        with st.sidebar:
            name = st.session_state.user.get('name', '')
            st.markdown(f"### Hi {name if name else st.session_state.user['email']}")
            
            # Navigation buttons
            if st.button("📊 View Statistics"):
                st.session_state.show_stats = True
            
            if st.button("💬 Chat"):
                st.session_state.show_stats = False
                
            if st.button("Logout"):
                st.session_state.user = None
                st.session_state.show_stats = False
                st.session_state.chat_history = [
                    {"role": "system", "message": DEFAULT_SYSTEM_PROMPT}
                ]
                st.rerun()
            
            # Clear chat button
            if st.button("Clear Chat"):
                # Keep the system prompt but clear the rest
                system_content = st.session_state.chat_history[0]["message"] if st.session_state.chat_history else ""
                st.session_state.chat_history = [
                    {"role": "system", "message": system_content}
                ]
                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                st.rerun()
