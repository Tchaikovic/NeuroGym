"""
Main Streamlit application for the Cohere AI Tutor
Refactored version with modular structure
"""
import streamlit as st

# Import page modules
from components.auth import show_login_register
from components.statistics import show_statistics  
from components.chat import show_chat
from components.sidebar import show_sidebar

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

if "show_stats" not in st.session_state:
    st.session_state.show_stats = False

# Show sidebar if user is logged in
show_sidebar()

# Main content area
st.title("Cohere Agent Chat")

# Route to appropriate page based on user state
if st.session_state.user is None:
    # User not logged in - show authentication
    show_login_register()
elif st.session_state.user and st.session_state.show_stats:
    # User logged in and viewing statistics
    show_statistics()
else:
    # User logged in and using chat
    show_chat()
