"""
LangChain-based chat memory management for the AI Tutor platform
"""
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from config import MONGODB_URI, DATABASE_NAME
import streamlit as st

class TutorChatMemory:
    """LangChain-based chat memory for the AI tutor"""
    
    def __init__(self, user_email: str, session_id: str = None):
        self.user_email = user_email
        self.session_id = session_id or user_email
        
        # MongoDB connection string for LangChain
        connection_string = f"{MONGODB_URI}{DATABASE_NAME}"
        
        # Initialize MongoDB chat message history
        self.message_history = MongoDBChatMessageHistory(
            connection_string=connection_string,
            session_id=self.session_id,
            collection_name="langchain_chat_history"
        )
        
        # Initialize conversation memory with window buffer (simpler than summary buffer)
        self.memory = ConversationBufferWindowMemory(
            chat_memory=self.message_history,
            k=50,  # Keep last 50 messages
            return_messages=True,
            memory_key="chat_history"
        )
    
    def add_user_message(self, message: str):
        """Add a user message to the chat history"""
        self.memory.chat_memory.add_user_message(message)
    
    def add_ai_message(self, message: str):
        """Add an AI message to the chat history"""
        self.memory.chat_memory.add_ai_message(message)
    
    def add_system_message(self, message: str):
        """Add a system message to the chat history"""
        # For system messages, we'll add them directly to the message history
        system_msg = SystemMessage(content=message)
        self.message_history.add_message(system_msg)
    
    def get_messages(self) -> list:
        """Get all messages in a format compatible with Cohere API"""
        messages = []
        
        # Get messages from memory
        memory_messages = self.memory.chat_memory.messages
        
        for msg in memory_messages:
            if isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
        
        return messages
    
    def get_memory_variables(self) -> dict:
        """Get memory variables for prompt formatting"""
        return self.memory.load_memory_variables({})
    
    def clear_history(self, keep_system_prompt: bool = True):
        """Clear chat history, optionally keeping system prompt"""
        if keep_system_prompt:
            # Save system message if it exists
            messages = self.message_history.messages
            system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
            
            # Clear all messages
            self.message_history.clear()
            
            # Re-add system messages
            for sys_msg in system_messages:
                self.message_history.add_message(sys_msg)
        else:
            self.message_history.clear()
    
    def update_system_message(self, new_system_prompt: str):
        """Update the system message (replace existing one)"""
        messages = self.message_history.messages
        
        # Remove existing system messages
        non_system_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        
        # Clear and rebuild with new system message
        self.message_history.clear()
        self.add_system_message(new_system_prompt)
        
        # Re-add non-system messages
        for msg in non_system_messages:
            self.message_history.add_message(msg)
    
    def save_tool_call(self, tool_name: str, tool_args: dict, tool_result: any):
        """Save tool call information as part of conversation"""
        tool_message = f"Tool used: {tool_name} with args: {tool_args}"
        self.add_ai_message(tool_message)

class LangChainChatManager:
    """Manager class for handling multiple user chat sessions"""
    
    _instances = {}
    
    @classmethod
    def get_chat_memory(cls, user_email: str) -> TutorChatMemory:
        """Get or create a chat memory instance for a user"""
        if user_email not in cls._instances:
            cls._instances[user_email] = TutorChatMemory(user_email)
        return cls._instances[user_email]
    
    @classmethod
    def clear_user_session(cls, user_email: str):
        """Clear a user's chat session from memory"""
        if user_email in cls._instances:
            del cls._instances[user_email]

# Legacy compatibility functions for existing code
def save_chat_history_langchain(user_email: str, chat_history: list):
    """Save chat history using LangChain (compatibility function)"""
    memory = LangChainChatManager.get_chat_memory(user_email)
    
    # Clear existing history
    memory.clear_history(keep_system_prompt=False)
    
    # Add messages from the provided history
    for msg in chat_history:
        role = msg.get("role", "")
        content = msg.get("message", msg.get("content", ""))
        
        if role == "system":
            memory.add_system_message(content)
        elif role == "user":
            memory.add_user_message(content)
        elif role == "assistant":
            memory.add_ai_message(content)

def load_chat_history_langchain(user_email: str) -> list:
    """Load chat history using LangChain (compatibility function)"""
    memory = LangChainChatManager.get_chat_memory(user_email)
    return memory.get_messages()

def convert_langchain_to_cohere_format(user_email: str) -> list:
    """Convert LangChain memory to Cohere API format"""
    memory = LangChainChatManager.get_chat_memory(user_email)
    return memory.get_messages()
