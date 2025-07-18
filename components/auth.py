"""
Authentication page - handles login and registration
"""
import streamlit as st
from database import authenticate_user, register_user, save_chat_history, serialize_chat_history
from config import TUTOR_SYSTEM_PROMPT

def show_login_register():
    """Display login and registration tabs"""
    tab_login, tab_register = st.tabs(["Login", "Register"])
    
    with tab_login:
        st.subheader("Login")
        with st.form(key="login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Login")
        
        if login_submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state.user = user
                # AI Tutor system prompt
                system_prompt = TUTOR_SYSTEM_PROMPT.format(
                    name=user.get('name', ''),
                    age=user.get('age', '')
                )
                
                # Load or create chat history
                from database import load_chat_history
                existing_history = load_chat_history(email)
                if existing_history:
                    # Update the first system message if needed
                    if existing_history and existing_history[0]["role"] == "system":
                        existing_history[0]["content"] = system_prompt
                    else:
                        existing_history = [{"role": "system", "content": system_prompt}] + existing_history
                    st.session_state.chat_history = existing_history
                else:
                    st.session_state.chat_history = [{"role": "system", "content": system_prompt}]
                
                                # Save updated chat history with personalized prompt
                save_chat_history(email, st.session_state.chat_history)
                st.success(f"Welcome, {user['email']}!")
                
                # Add a casual welcome message from the agent - no immediate topic request
                welcome_msg = {"role": "assistant", "content": f"Hi {user.get('name', '')}! 👋 I'm your AI tutor. How are you doing today? Feel free to chat with me about anything!"}
                st.session_state.chat_history.append(welcome_msg)
                save_chat_history(email, st.session_state.chat_history)
                st.rerun()
            else:
                st.error("Invalid credentials or user not found.")
            st.stop()
    
    with tab_register:
        st.subheader("Register")
        with st.form(key="register_form"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            name = st.text_input("Name")
            age = st.text_input("Age")
            register_submitted = st.form_submit_button("Register")
        
        if register_submitted:
            success, result = register_user(email, password, name, age)
            if success:
                st.session_state.user = result
                # AI Tutor system prompt
                system_prompt = TUTOR_SYSTEM_PROMPT.format(
                    name=name,
                    age=int(age)
                )
                
                st.session_state.chat_history = [{"role": "system", "content": system_prompt}]
                save_chat_history(email, st.session_state.chat_history)
                
                # Add a welcome message from the agent
                save_chat_history(email, st.session_state.chat_history)
                
                # Add a casual welcome message from the agent - no immediate topic request
                welcome_msg = {"role": "assistant", "content": f"Hi {name}! 👋 Welcome to our tutoring platform. I'm excited to help you learn! How has your day been?"}
                st.session_state.chat_history.append(welcome_msg)
                save_chat_history(email, st.session_state.chat_history)
                st.success(f"Account created. Welcome, {email}!")
                st.rerun()
            else:
                st.error(result)
            st.stop()
