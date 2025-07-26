"""
Direct MongoDB chat memory management for the AI Tutor platform
Simple and efficient chat storage without external dependencies
"""
from pymongo import MongoClient
from src.config import MONGODB_URI, DATABASE_NAME
from datetime import datetime
import json

class SimpleChatMemory:
    """Simple MongoDB-based chat memory for the AI tutor"""
    
    def __init__(self, user_email: str):
        self.user_email = user_email
        
        # MongoDB setup
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db["chat_history"]
    
    def _clean_message_for_storage(self, message: dict) -> dict:
        """Clean message to remove non-serializable objects like ToolCallV2Function"""
        cleaned_message = {}
        
        for key, value in message.items():
            # Skip tool_calls and tool_plan as they contain non-serializable ToolCallV2Function objects
            if key in ['tool_calls', 'tool_plan']:
                continue
                
            # Handle nested objects
            if isinstance(value, dict):
                cleaned_message[key] = self._clean_dict_for_storage(value)
            elif isinstance(value, list):
                cleaned_message[key] = self._clean_list_for_storage(value)
            else:
                # Try to serialize to check if it's JSON serializable
                try:
                    json.dumps(value)
                    cleaned_message[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable values (like ToolCallV2Function)
                    continue
                    
        return cleaned_message
    
    def _clean_dict_for_storage(self, data: dict) -> dict:
        """Recursively clean dictionary for storage"""
        cleaned = {}
        for key, value in data.items():
            try:
                json.dumps(value)
                cleaned[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable values
                continue
        return cleaned
    
    def _clean_list_for_storage(self, data: list) -> list:
        """Clean list by removing non-serializable items like ToolCallV2Function"""
        cleaned = []
        for item in data:
            try:
                # Check if item contains ToolCallV2Function by attempting serialization
                json.dumps(item)
                cleaned.append(item)
            except (TypeError, ValueError):
                # Skip non-serializable items (ToolCallV2Function objects)
                continue
        return cleaned
    
    def save_chat_history(self, chat_history: list):
        """Save complete chat history for user, excluding non-serializable objects"""
        # Clean the chat history to remove ToolCallV2Function and other non-serializable objects
        cleaned_history = []
        
        for message in chat_history:
            if isinstance(message, dict):
                cleaned_message = self._clean_message_for_storage(message)
                
                # Only include messages that have essential fields after cleaning
                # Skip messages that only had tool_calls (as those are not serializable)
                if cleaned_message.get('role') and (
                    cleaned_message.get('content') or 
                    cleaned_message.get('role') == 'tool'
                ):
                    cleaned_history.append(cleaned_message)
        
        # Update or insert the user's chat history
        self.collection.update_one(
            {"user_email": self.user_email},
            {
                "$set": {
                    "user_email": self.user_email,
                    "messages": cleaned_history,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
    
    def load_chat_history(self) -> list:
        """Load chat history for user"""
        doc = self.collection.find_one({"user_email": self.user_email})
        if doc and "messages" in doc:
            return doc["messages"]
        return []
    
    def clear_history(self):
        """Clear chat history for user"""
        self.collection.delete_one({"user_email": self.user_email})
    
    def add_message(self, message: dict):
        """Add a single message to chat history"""
        current_history = self.load_chat_history()
        cleaned_message = self._clean_message_for_storage(message)
        
        # Only add if the message has essential fields after cleaning
        if cleaned_message.get('role') and (
            cleaned_message.get('content') or 
            cleaned_message.get('role') == 'tool'
        ):
            current_history.append(cleaned_message)
            self.save_chat_history(current_history)

class ChatManager:
    """Manager class for handling multiple user chat sessions"""
    
    _instances = {}
    
    @classmethod
    def get_chat_memory(cls, user_email: str) -> SimpleChatMemory:
        """Get or create a chat memory instance for a user"""
        if user_email not in cls._instances:
            cls._instances[user_email] = SimpleChatMemory(user_email)
        return cls._instances[user_email]
    
    @classmethod
    def clear_user_session(cls, user_email: str):
        """Clear a user's chat session from memory"""
        if user_email in cls._instances:
            del cls._instances[user_email]

# Direct storage functions - no conversion needed
def save_chat_history_direct(user_email: str, chat_history: list):
    """Save chat history directly to MongoDB in Cohere API v2 format"""
    memory = ChatManager.get_chat_memory(user_email)
    memory.save_chat_history(chat_history)

def load_chat_history_direct(user_email: str) -> list:
    """Load chat history directly from MongoDB in Cohere API v2 format"""
    memory = ChatManager.get_chat_memory(user_email)
    return memory.load_chat_history()
