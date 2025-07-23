"""
Database operations for the Cohere Agent application
"""
import json
from pymongo import MongoClient
import streamlit as st
from config import MONGODB_URI, DATABASE_NAME, COLLECTIONS

# LangChain imports for memory management
from langchain_memory import (
    LangChainChatManager, 
    save_chat_history_langchain, 
    load_chat_history_langchain,
    convert_langchain_to_cohere_format
)

# MongoDB setup
client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

# Collections
quizzes_collection = db[COLLECTIONS["quizzes"]]
users_collection = db[COLLECTIONS["users"]]
chats_collection = db[COLLECTIONS["chats"]]
answers_collection = db[COLLECTIONS["answers"]]
topics_collection = db[COLLECTIONS["topics"]]
password_resets_collection = db[COLLECTIONS["password_resets"]]
quiz_results_collection = db["quiz_results"]  # For storing quiz scores and performance

def store_topic(user_email, topic):
    """Store topic in topics_collection if it doesn't already exist (fuzzy matching)"""
    import re
    from difflib import SequenceMatcher
    
    def normalize_topic(topic_str):
        """Normalize topic string for comparison"""
        if not topic_str:
            return ""
        # Convert to lowercase, remove extra spaces, punctuation
        normalized = re.sub(r'[^\w\s]', '', topic_str.lower())
        return ' '.join(normalized.split())
    
    def topics_are_similar(topic1, topic2, threshold=0.8):
        """Check if two topics are similar using sequence matching"""
        norm1 = normalize_topic(topic1)
        norm2 = normalize_topic(topic2)
        return SequenceMatcher(None, norm1, norm2).ratio() >= threshold
    
    # Normalize the new topic
    normalized_new_topic = normalize_topic(topic)
    
    # Check if a similar topic already exists
    existing_topics = list(topics_collection.find({}))
    for existing_topic_doc in existing_topics:
        existing_topic = existing_topic_doc.get('topic', '')
        if topics_are_similar(topic, existing_topic):
            # Topic already exists, return the existing topic name
            return existing_topic
    
    # Topic doesn't exist, create new one
    topics_collection.insert_one({
        "topic": topic,
        "normalized": normalized_new_topic,
        "created_date": __import__('datetime').datetime.now().isoformat(),
        "created_by": user_email
    })
    return topic

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
    # Get topics worked on by checking quizzes taken
    quiz_answers = list(answers_collection.find({"user_email": user_email}))
    quizzes_taken = len(quiz_answers)
    
    # Get unique topics from quizzes taken
    user_topics = set()
    for answer_doc in quiz_answers:
        quiz_id = answer_doc["quiz_id"]
        try:
            quiz_doc = quizzes_collection.find_one({"_id": __import__('bson').ObjectId(quiz_id)})
            if quiz_doc and quiz_doc.get("topic"):
                user_topics.add(quiz_doc["topic"])
        except:
            continue
    
    topics_count = len(user_topics)
    topics_list = [{"topic": topic} for topic in user_topics]
    
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
    """Save chat history using LangChain memory management"""
    save_chat_history_langchain(user_email, chat_history)

def load_chat_history(user_email):
    """Load chat history using LangChain memory management"""
    return load_chat_history_langchain(user_email)

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
    
    # Create user with initial XP
    users_collection.insert_one({
        "email": email, 
        "password": password, 
        "name": name, 
        "age": age_int,
        "xp": 10  # Welcome bonus XP
    })
    return True, {"email": email, "name": name, "age": age_int}

def get_quiz_by_id(quiz_id):
    """Get quiz document by ID"""
    try:
        return quizzes_collection.find_one({"_id": __import__('bson').ObjectId(quiz_id)})
    except:
        return None

def save_quiz_answers(user_email, quiz_id, answers, score=None):
    """Save user's quiz answers with optional score"""
    update_data = {
        "answers": answers,
        "completed_at": __import__('datetime').datetime.now().isoformat()
    }
    if score is not None:
        update_data["score"] = score
    
    answers_collection.update_one(
        {"user_email": user_email, "quiz_id": quiz_id},
        {"$set": update_data},
        upsert=True
    )

def get_user_topics(user_email=None):
    """Get all available topics (not user-specific anymore)"""
    return list(topics_collection.find({}))

def get_user_studied_topics(user_email):
    """Get topics that a specific user has actually studied (taken quizzes on)"""
    quiz_answers = list(answers_collection.find({"user_email": user_email}))
    user_topics = set()
    
    for answer_doc in quiz_answers:
        quiz_id = answer_doc["quiz_id"]
        try:
            quiz_doc = quizzes_collection.find_one({"_id": __import__('bson').ObjectId(quiz_id)})
            if quiz_doc and quiz_doc.get("topic"):
                user_topics.add(quiz_doc["topic"])
        except:
            continue
    
    return [{"topic": topic} for topic in user_topics]

def get_quiz_leaderboard(quiz_id, limit=10):
    """Get leaderboard for a specific quiz"""
    pipeline = [
        {"$match": {"quiz_id": quiz_id, "score": {"$exists": True}}},
        {"$sort": {"score": -1, "completed_at": 1}},  # Sort by score desc, then by completion time asc
        {"$limit": limit},
        {"$project": {"user_email": 1, "score": 1, "completed_at": 1}}
    ]
    return list(answers_collection.aggregate(pipeline))

def get_topic_quiz_statistics(topic):
    """Get statistics for all quizzes on a specific topic"""
    # Find all quizzes for this topic
    topic_quizzes = list(quizzes_collection.find({"topic": topic}))
    
    stats = {
        "topic": topic,
        "total_quizzes": len(topic_quizzes),
        "quiz_stats": []
    }
    
    for quiz in topic_quizzes:
        quiz_id = str(quiz["_id"])
        # Get all scores for this quiz
        quiz_answers = list(answers_collection.find({"quiz_id": quiz_id, "score": {"$exists": True}}))
        
        if quiz_answers:
            scores = [answer["score"] for answer in quiz_answers]
            quiz_stat = {
                "quiz_id": quiz_id,
                "title": quiz.get("title", "Untitled"),
                "total_attempts": len(quiz_answers),
                "average_score": sum(scores) / len(scores),
                "highest_score": max(scores),
                "lowest_score": min(scores)
            }
            stats["quiz_stats"].append(quiz_stat)
    
    return stats

def count_user_messages(chat_history):
    """Count the number of user messages in chat history (excluding system messages)"""
    return len([msg for msg in chat_history if msg["role"] == "user"])

def add_xp(user_email, xp_amount, reason):
    """Add XP to a user and return new total"""
    users_collection.update_one(
        {"email": user_email},
        {"$inc": {"xp": xp_amount}},
        upsert=True
    )
    
    # Get updated XP total
    user = users_collection.find_one({"email": user_email})
    new_xp = user.get("xp", 0)
    
    return new_xp

def get_user_xp(user_email):
    """Get current XP for a user"""
    user = users_collection.find_one({"email": user_email})
    return user.get("xp", 0) if user else 0

def calculate_level(xp):
    """Calculate level based on XP (every 100 XP = 1 level)"""
    return xp // 100 + 1

def xp_to_next_level(xp):
    """Calculate XP needed to reach next level"""
    current_level = calculate_level(xp)
    xp_for_next_level = current_level * 100
    return xp_for_next_level - xp

def create_password_reset_token(email):
    """Create a password reset token for the user"""
    import secrets
    import datetime
    
    # Check if user exists
    user = users_collection.find_one({"email": email})
    if not user:
        return None
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    
    # Token expires in 1 hour
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
    
    # Store token in database (remove any existing tokens for this email)
    password_resets_collection.delete_many({"email": email})
    password_resets_collection.insert_one({
        "email": email,
        "token": token,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.datetime.now()
    })
    
    return token

def verify_reset_token(token):
    """Verify if a reset token is valid and not expired"""
    import datetime
    
    reset_doc = password_resets_collection.find_one({
        "token": token,
        "used": False,
        "expires_at": {"$gt": datetime.datetime.now()}
    })
    
    return reset_doc

def reset_password(token, new_password):
    """Reset password using a valid token"""
    import datetime
    
    # Verify token
    reset_doc = verify_reset_token(token)
    if not reset_doc:
        return False, "Invalid or expired reset token"
    
    # Update user password
    result = users_collection.update_one(
        {"email": reset_doc["email"]},
        {"$set": {"password": new_password}}
    )
    
    if result.modified_count > 0:
        # Mark token as used
        password_resets_collection.update_one(
            {"token": token},
            {"$set": {"used": True, "used_at": datetime.datetime.now()}}
        )
        return True, "Password reset successfully"
    else:
        return False, "Failed to update password"

def debug_user_password(email):
    """Debug function to check what password is stored for a user"""
    user = users_collection.find_one({"email": email})
    if user:
        print(f"DEBUG: User {email} found with password: '{user.get('password')}'")
        return user.get('password')
    else:
        print(f"DEBUG: User {email} not found")
        return None

def send_password_reset_email(email, token):
    """Send password reset email (simplified version - in production use proper email service)"""
    try:
        from config import EMAIL_CONFIG
        
        # Create reset link (in production, this should be your actual domain)
        reset_link = f"http://localhost:8501/?reset_token={token}"
        
        # For development, just return the reset link instead of sending email
        # In production, you would implement proper SMTP email sending
        return True, f"Reset link (for development): {reset_link}"
        
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"
