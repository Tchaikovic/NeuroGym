"""
Main Streamlit application for AI Tutor platform
"""
import streamlit as st
from components.auth import show_login_register
from components.chat import show_chat
from components.statistics import show_statistics
from components.sidebar import show_sidebar

# Page config
st.set_page_config(
    page_title="AI Tutor Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "show_stats" not in st.session_state:
    st.session_state.show_stats = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def main():
    """Main application logic"""
    
    # Check if user is logged in
    if st.session_state.user is None:
        # Show authentication page
        show_login_register()
    else:
        # Show sidebar for logged-in users
        show_sidebar()
        
        # Show appropriate page based on user selection
        if st.session_state.show_stats:
            show_statistics()
        else:
            show_chat()

if __name__ == "__main__":
    main()
