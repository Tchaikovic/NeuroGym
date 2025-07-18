"""
Database operations for the Cohere Agent application
"""
import json
from pymongo import MongoClient
import streamlit as st
from config import MONGODB_URI, DATABASE_NAME, COLLECTIONS

# MongoDB setup
client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

# Collections
quizzes_collection = db[COLLECTIONS["quizzes"]]
users_collection = db[COLLECTIONS["users"]]
chats_collection = db[COLLECTIONS["chats"]]
answers_collection = db[COLLECTIONS["answers"]]
topics_collection = db[COLLECTIONS["topics"]]

def store_topic(user_email, topic):
    """Store topic in topics_collection"""
    topics_collection.insert_one({
        "user_email": user_email,
        "topic": topic,
        "date": __import__('datetime').datetime.now().isoformat()
    })

def serialize_chat_history(history):
    """Helper to serialize chat history for MongoDB"""
    def serialize_item(item):
        if isinstance(item, dict):
            return {k: serialize_item(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [serialize_item(i) for i in item]
        elif hasattr(item, "__dict__"):  # Cohere objects
            # Try to convert to dict, fallback to str
            try:
                d = dict(item.__dict__)
                # Remove any non-serializable fields recursively
                return serialize_item(d)
            except Exception:
                return str(item)
        else:
            return item
    return [serialize_item(msg) for msg in history]

def get_user_statistics(user_email):
    """Get comprehensive statistics for a user"""
    # Get topics worked on
    topics_count = topics_collection.count_documents({"user_email": user_email})
    topics_list = list(topics_collection.find({"user_email": user_email}))
    
    # Get quizzes taken
    quiz_answers = list(answers_collection.find({"user_email": user_email}))
    quizzes_taken = len(quiz_answers)
    
    # Calculate correct/incorrect answers
    total_questions = 0
    correct_answers = 0
    incorrect_answers = 0
    
    for answer_doc in quiz_answers:
        quiz_id = answer_doc["quiz_id"]
        user_answers = answer_doc["answers"]
        
        # Get the quiz to compare answers
        try:
            quiz_doc = quizzes_collection.find_one({"_id": __import__('bson').ObjectId(quiz_id)})
            if quiz_doc and quiz_doc.get("questions"):
                for i, question in enumerate(quiz_doc["questions"]):
                    if i < len(user_answers):
                        total_questions += 1
                        if user_answers[i] == question.get("answer"):
                            correct_answers += 1
                        else:
                            incorrect_answers += 1
        except:
            continue
    
    return {
        "topics_count": topics_count,
        "topics_list": topics_list,
        "quizzes_taken": quizzes_taken,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers
    }

def save_chat_history(user_email, chat_history):
    """Save chat history to MongoDB"""
    chats_collection.update_one(
        {"email": user_email},
        {"$set": {"history": serialize_chat_history(chat_history)}},
        upsert=True
    )

def load_chat_history(user_email):
    """Load existing chat history from MongoDB"""
    chat_doc = chats_collection.find_one({"email": user_email})
    if chat_doc and "history" in chat_doc:
        return chat_doc["history"]
    return None

def authenticate_user(email, password):
    """Authenticate user login"""
    user = users_collection.find_one({"email": email})
    if user and user.get("password") == password:
        return {"email": email, "name": user.get("name", ""), "age": user.get("age", "")}
    return None

def register_user(email, password, name, age):
    """Register a new user"""
    # Check if user already exists
    if users_collection.find_one({"email": email}):
        return False, "User already exists. Please login."
    
    # Validate age is a number
    try:
        age_int = int(age)
    except ValueError:
        return False, "Please enter a valid age (number)."
    
    # Create user
    users_collection.insert_one({"email": email, "password": password, "name": name, "age": age_int})
    return True, {"email": email, "name": name, "age": age_int}

def get_quiz_by_id(quiz_id):
    """Get quiz document by ID"""
    try:
        return quizzes_collection.find_one({"_id": __import__('bson').ObjectId(quiz_id)})
    except:
        return None

def save_quiz_answers(user_email, quiz_id, answers):
    """Save user's quiz answers"""
    answers_collection.update_one(
        {"user_email": user_email, "quiz_id": quiz_id},
        {"$set": {"answers": answers}},
        upsert=True
    )

def get_user_topics(user_email):
    """Get all topics for a user"""
    return list(topics_collection.find({"user_email": user_email}))

def count_user_messages(chat_history):
    """Count the number of user messages in chat history (excluding system messages)"""
    return len([msg for msg in chat_history if msg["role"] == "user"])
