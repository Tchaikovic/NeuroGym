"""
Chat page - handles the main chat interface with AI tutor
"""
import streamlit as st
import json
import cohere
from ..database import (
    load_chat_history, save_chat_history, store_topic, 
    get_quiz_by_id, save_quiz_answers, db, get_user_topics, count_user_messages
)
from ..config import COHERE_API_KEY, COHERE_MODEL, TUTOR_SYSTEM_PROMPT

# Import profiler
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ..profiler import profiler, timer, profile_chat_operation
from components.performance_dashboard import add_performance_monitoring

# Cohere setup
co = cohere.ClientV2(api_key=COHERE_API_KEY)

def extract_text_from_content(content):
    """Extract text content from various response formats"""
    if not content:
        return ""
    
    # Handle string content directly
    if isinstance(content, str):
        return content
    
    # Handle list of content items (v2 API format)
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if hasattr(item, 'text'):
                text_parts.append(item.text)
            elif isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            elif isinstance(item, str):
                text_parts.append(item)
        return ' '.join(text_parts)
    
    # Handle single content item with text attribute
    if hasattr(content, 'text'):
        return content.text
    
    # Fallback to string conversion
    return str(content)

# Tool functions
@profile_chat_operation("create_quiz_tool")
def create_quiz(title: str, questions: list, difficulty: str = "medium", topic: str = None):
    """Create a quiz with title, questions, difficulty, and topic"""
    from database import quizzes_collection, topics_collection
    import re
    from difflib import SequenceMatcher
    
    # Each question must be a dict with 'question', 'choices', and 'answer'
    
    # Get user_email from session state
    user_email = st.session_state.user["email"]
    
    # Handle topic registration using the improved topic selection logic
    if topic:
        with timer("topic_selection_in_quiz"):
            from database import handle_user_topic_selection
            topic_id, final_topic_name, is_new_topic = handle_user_topic_selection(user_email, topic)
    
    # Create the quiz document
    with timer("quiz_database_insert"):
        quiz_doc = {
            "title": title,
            "questions": questions,
            "difficulty": difficulty,
            "topic": topic,
            "user_email": user_email,
            "created_at": __import__('datetime').datetime.now()
        }
        
        # Insert quiz into database
        result = quizzes_collection.insert_one(quiz_doc)
        quiz_id = str(result.inserted_id)
    
    # Return success message with quiz info
    return {
        "status": "success",
        "message": f"Quiz '{title}' created successfully!",
        "quiz_id": quiz_id,
        "topic": topic,
        "question_count": len(questions),
        "difficulty": difficulty
    }

@profile_chat_operation("start_new_topic_tool")
def start_new_topic(topic_name: str):
    """Start a new learning topic for the student"""
    try:
        # Get user_email from session state
        user_email = st.session_state.user["email"]
        
        # Handle topic registration using the improved topic selection logic
        with timer("handle_user_topic_selection"):
            from database import handle_user_topic_selection
            topic_id, final_topic_name, is_new_topic = handle_user_topic_selection(user_email, topic_name)
        
        if is_new_topic:
            message = f"Great! I've started a new topic: '{final_topic_name}'. What specific aspect would you like to explore first?"
        else:
            message = f"Welcome back to '{final_topic_name}'! Let's continue where we left off. What would you like to work on?"
        
        return {
            "status": "success",
            "message": message,
            "topic_id": topic_id,
            "topic_name": final_topic_name,
            "is_new_topic": is_new_topic
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error starting topic: {str(e)}"
        }

@profile_chat_operation("show_quiz_leaderboard_tool")
def show_quiz_leaderboard():
    """Show quiz performance statistics"""
    try:
        # Get user_email from session state
        user_email = st.session_state.user["email"]
        
        with timer("get_user_statistics"):
            from database import get_user_statistics
            stats = get_user_statistics(user_email)
        
        return {
            "status": "success",
            "statistics": stats,
            "message": f"You've worked on {stats['topics_count']} topics and taken {stats['quizzes_taken']} quizzes!"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving statistics: {str(e)}"
        }

@profile_chat_operation("get_learning_topics_tool")
def get_learning_topics():
    """Get list of topics the student has worked on"""
    try:
        # Get user_email from session state
        user_email = st.session_state.user["email"]
        
        with timer("get_user_topics"):
            from database import get_user_topics
            topics = get_user_topics(user_email)
        
        if not topics:
            return {
                "status": "success",
                "topics": [],
                "message": "You haven't started any topics yet. What would you like to learn about?"
            }
        
        topic_list = [{"topic": t["topic"], "started_date": t.get("started_date")} for t in topics]
        
        return {
            "status": "success",
            "topics": topic_list,
            "message": f"You've worked on {(topics)} topics so far!"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving topics: {str(e)}"
        }

# Tool definitions for Cohere - Educational tools only
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_quiz",
            "description": "Creates a quiz with a title, topic, difficulty, and a list of questions. Only use this when the student explicitly asks for a quiz or test on a specific topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string", 
                        "description": "A clear, descriptive title for the quiz (e.g., 'Python Basics Quiz', 'Math Algebra Test')"
                    },
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "The question text"
                                },
                                "choices": {
                                    "type": "array", 
                                    "items": {"type": "string"},
                                    "description": "Array of 3-4 multiple choice options",
                                    "minItems": 3,
                                    "maxItems": 4
                                },
                                "answer": {
                                    "type": "string",
                                    "description": "The correct answer - must be one of the choices"
                                }
                            },
                            "required": ["question", "choices", "answer"]
                        },
                        "description": "Array of 3-5 multiple choice questions",
                        "minItems": 3,
                        "maxItems": 5
                    },
                    "difficulty": {
                        "type": "string", 
                        "enum": ["easy", "medium", "hard"],
                        "description": "The difficulty level of the quiz"
                    },
                    "topic": {
                        "type": "string", 
                        "description": "The specific topic or subject area for this quiz"
                    }
                },
                "required": ["title", "questions", "difficulty", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_new_topic",
            "description": "Start a new learning topic when the student expresses interest in learning about a specific subject. Only use this when the student mentions wanting to learn about a new topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string", 
                        "description": "The specific topic name the student wants to learn (e.g., 'Python Programming', 'Algebra', 'World History')"
                    }
                },
                "required": ["topic_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_quiz_leaderboard",
            "description": "Display quiz performance statistics and achievements. Only use this when the student asks about their scores, performance, or wants to see statistics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_learning_topics",
            "description": "Retrieve and display the topics that the student has worked on. Only use this when the student asks what topics they've studied or wants to see their learning history.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Map function names to Python functions for tool execution
functions_map = {
    "create_quiz": create_quiz,
    "start_new_topic": start_new_topic,
    "show_quiz_leaderboard": show_quiz_leaderboard,
    "get_learning_topics": get_learning_topics
}



def show_chat():
    """Display the main chat interface"""
    # Add performance monitoring to sidebar
    add_performance_monitoring()
    
    # Ensure chat history exists for logged-in users
    with timer("load_chat_history"):
        if "chat_history" not in st.session_state:
            # Load existing chat history from MongoDB  
            existing_history = load_chat_history(st.session_state.user["email"])
            if existing_history:
                st.session_state.chat_history = existing_history
            else:
                # Default tutor system prompt for new users
                system_prompt = TUTOR_SYSTEM_PROMPT.format(
                    name=st.session_state.user.get('name', ''),
                    age=st.session_state.user.get('age', '')
                )
                # Add welcome message for new users
                welcome_message = f"Hello {st.session_state.user.get('name', 'there')}! 👋 I'm your AI tutor, and I'm here to help you learn and grow. I can create quizzes, explain concepts, and guide you through various topics. What would you like to learn about today?"
                
                st.session_state.chat_history = [
                    {"role": "system", "content": system_prompt},
                    {"role": "assistant", "content": welcome_message}
                ]

    # Display chat history
    with timer("render_chat_history"):
        for idx, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            elif msg["role"] == "assistant":
                # Extract text content properly for display
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if hasattr(item, 'text'):
                            text_content += item.text
                        elif isinstance(item, dict) and 'text' in item:
                            text_content += item['text']
                        elif isinstance(item, str):
                            text_content += item
                    content = text_content
                elif hasattr(content, 'text'):
                    content = content.text
                else:
                    content = str(content)
                
                # Only display assistant messages that have actual content
                # Skip empty messages that might be intermediate tool planning messages
                if content and content.strip() and content.strip() != "[No response content]":
                    st.markdown(f"**Agent:** {content}")
            elif msg["role"] == "tool" and msg.get("content") and st.session_state.user:
                # Render quiz as interactive radio buttons
                for item in msg["content"]:
                    try:
                        data = json.loads(item["document"]["data"])
                        if data.get("quiz_id") and data.get("is_success"):
                            quiz_id = data["quiz_id"]
                            quiz_doc = get_quiz_by_id(quiz_id)
                            if quiz_doc and quiz_doc.get("questions"):
                                # Only display if all questions are multiple choice with correct answer
                                all_mc = all(isinstance(q, dict) and "question" in q and "choices" in q and "answer" in q for q in quiz_doc["questions"])
                                if all_mc:
                                    st.markdown(f"### Quiz: {quiz_doc.get('title','')}")
                                    quiz_key = f"quiz_{quiz_id}_answers"
                                    if quiz_key not in st.session_state:
                                        st.session_state[quiz_key] = [None] * len(quiz_doc["questions"])
                                    answers = []
                                    with st.form(key=f"quiz_form_{quiz_id}"):
                                        for i, q in enumerate(quiz_doc["questions"]):
                                            # Show choices as radio buttons
                                            ans = st.radio(q["question"], q["choices"], key=f"quiz_{quiz_id}_q{i}")
                                            answers.append(ans)
                                        submitted = st.form_submit_button("Submit Quiz Answers")
                                        if submitted:
                                            # Save answers to database
                                            save_quiz_answers(st.session_state.user["email"], quiz_id, answers)
                                            
                                            # Compare answers to correct ones
                                            correct = 0
                                            mistakes = []
                                            for i, q in enumerate(quiz_doc["questions"]):
                                                if answers[i] == q["answer"]:
                                                    correct += 1
                                                else:
                                                    mistakes.append({
                                                        "question": q["question"],
                                                        "your_answer": answers[i],
                                                        "correct_answer": q["answer"]
                                                    })
                                            
                                            feedback = f"Your answers have been recorded! You got {correct} out of {len(quiz_doc['questions'])} correct."
                                            if mistakes:
                                                feedback += "\n\nLet's review the questions you missed:"
                                                for m in mistakes:
                                                    feedback += f"\n- **Question:** {m['question']}\n  - Your answer: {m['your_answer']}\n  - Correct answer: {m['correct_answer']}"
                                                feedback += "\n\nWould you like me to explain any of these concepts in more detail, or shall we try another quiz? Feel free to ask me anything about these topics!"
                                            else:
                                                feedback += "\n\nExcellent work! Would you like to try a more challenging quiz, or shall we discuss any of these concepts further?"
                                            
                                            st.session_state.chat_history.append({"role": "assistant", "content": feedback})
                                            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                                            st.rerun()
                                    break
                    except Exception:
                        continue

    # Show topic selection after 2-3 user messages (inline with chat)
    user_message_count = count_user_messages(st.session_state.chat_history)
    if user_message_count >= 2 and user_message_count <= 4:
        # Check if we haven't already shown topic suggestion
        recent_messages = st.session_state.chat_history[-10:] if len(st.session_state.chat_history) >= 10 else st.session_state.chat_history
        topic_suggestion_shown = any("topic you'd like to work on" in str(msg.get("content", "")) for msg in recent_messages if msg["role"] == "assistant")
        
        # Also check if a topic has been selected recently (by looking for "I'd like to work on" messages)
        topic_selected_recently = any("I'd like to work on" in str(msg.get("content", "")) for msg in recent_messages if msg["role"] == "user")
        
        # Check if we're already in an active learning session (quiz created, quiz answered, etc.)
        learning_session_active = any(
            "quiz" in str(msg.get("content", "")).lower() or 
            msg.get("role") == "tool" or
            "Your answers have been recorded" in str(msg.get("content", ""))
            for msg in recent_messages
        )
        
        if not topic_suggestion_shown and not topic_selected_recently and not learning_session_active:
            st.markdown("### 📚 Ready to start learning?")
            
            # Get existing topics for this user
            existing_topics = get_user_topics(st.session_state.user["email"])
            
            if existing_topics:
                st.markdown("**Choose from your previous topics:**")
                cols = st.columns(min(len(existing_topics), 3))
                for i, topic_doc in enumerate(existing_topics):
                    col_idx = i % 3
                    with cols[col_idx]:
                        if st.button(f"📖 {topic_doc['topic']}", key=f"topic_btn_{topic_doc['_id']}"):
                            # Add user message selecting this topic
                            topic_message = f"I'd like to work on {topic_doc['topic']}"
                            st.session_state.chat_history.append({"role": "user", "content": topic_message})
                            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                            
                            # Get AI response for the topic selection
                            try:
                                response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
                            except Exception as e:
                                print(f"Topic selection error: {e}")
                                # Fallback without tools
                                response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history)
                            
                            # Process the AI response
                            if hasattr(response.message, "tool_calls") and response.message.tool_calls:
                                # Process assistant message with tool calls
                                assistant_msg = {"role": "assistant"}
                                assistant_msg["tool_calls"] = response.message.tool_calls
                                if hasattr(response.message, "tool_plan"):
                                    assistant_msg["tool_plan"] = response.message.tool_plan
                                
                                # Extract text content properly
                                if hasattr(response.message, "content") and response.message.content:
                                    if isinstance(response.message.content, list):
                                        text_content = ""
                                        for item in response.message.content:
                                            if hasattr(item, 'text'):
                                                text_content += item.text
                                            elif isinstance(item, dict) and 'text' in item:
                                                text_content += item['text']
                                            elif isinstance(item, str):
                                                text_content += item
                                        assistant_msg["content"] = text_content
                                    else:
                                        if hasattr(response.message.content, 'text'):
                                            assistant_msg["content"] = response.message.content.text
                                        else:
                                            assistant_msg["content"] = str(response.message.content)
                                
                                st.session_state.chat_history.append(assistant_msg)
                                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                                
                                # Execute tools
                                tool_messages = []
                                for tc in response.message.tool_calls:
                                    try:
                                        tool_args = json.loads(tc.function.arguments)
                                        
                                        # Validate that the function exists in our functions_map
                                        if tc.function.name not in functions_map:
                                            print(f"Unknown function called: {tc.function.name}")
                                            continue
                                        
                                        tool_result = functions_map[tc.function.name](**tool_args)
                                        
                                        if isinstance(tool_result, list):
                                            tool_content = [{"type": "document", "document": {"data": json.dumps(data)}} for data in tool_result]
                                        else:
                                            tool_content = [{"type": "document", "document": {"data": json.dumps(tool_result)}}]
                                        tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
                                    except Exception as tool_error:
                                        print(f"Tool execution error for {tc.function.name}: {tool_error}")
                                        # Create error response for this tool call
                                        error_content = [{"type": "document", "document": {"data": json.dumps({"status": "error", "message": f"Tool execution failed: {str(tool_error)}"})}}]
                                        tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": error_content})
                                
                                st.session_state.chat_history.extend(tool_messages)
                                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                                
                                # Get final assistant response after tool execution
                                try:
                                    response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
                                except Exception as e:
                                    print(f"Final response error: {e}")
                                    response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history)
                                
                                # Extract text content properly from final response
                                final_content = ""
                                if hasattr(response.message, "content") and response.message.content:
                                    if isinstance(response.message.content, list):
                                        for item in response.message.content:
                                            if hasattr(item, 'text'):
                                                final_content += item.text
                                            elif isinstance(item, dict) and 'text' in item:
                                                final_content += item['text']
                                            elif isinstance(item, str):
                                                final_content += item
                                    else:
                                        if hasattr(response.message.content, 'text'):
                                            final_content = response.message.content.text
                                        else:
                                            final_content = str(response.message.content)
                                
                                st.session_state.chat_history.append({"role": "assistant", "content": final_content})
                                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                            else:
                                # No tool calls - just add the assistant response
                                assistant_content = ""
                                if hasattr(response.message, "content") and response.message.content:
                                    if isinstance(response.message.content, list):
                                        for item in response.message.content:
                                            if hasattr(item, 'text'):
                                                assistant_content += item.text
                                            elif isinstance(item, dict) and 'text' in item:
                                                assistant_content += item['text']
                                            elif isinstance(item, str):
                                                assistant_content += item
                                    else:
                                        if hasattr(response.message.content, 'text'):
                                            assistant_content = response.message.content.text
                                        else:
                                            assistant_content = str(response.message.content)
                                
                                st.session_state.chat_history.append({"role": "assistant", "content": assistant_content})
                                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                            
                            st.rerun()
                
                st.markdown("**Or start a new topic by typing below:**")
            else:
                st.markdown("**What topic would you like to work on? Type it in the chat below!**")

    # Chat input form
    with st.form(key="chat_form_main", clear_on_submit=True):
        user_input = st.text_input("Type your message:", key="chat_user_input", placeholder="Type your message and press Enter")
        submitted = st.form_submit_button("Send")

    if submitted and user_input:
        with timer("total_chat_processing", show_result=True):
            print(f"User input: {user_input}")  # Debugging line to check user input
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
                    
            # Save chat history after user message
            with timer("save_chat_history_user"):
                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
            
            # Get AI response
            try:
                # Try with tools first
                with timer("cohere_api_call_with_tools"):
                    response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
            except Exception as e:
                print(f"Tool calling error: {e}")
                # If tool calling fails (e.g., hallucinated tools), retry without tools
                try:
                    with timer("cohere_api_call_fallback"):
                        response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history)
                except Exception as e2:
                    print(f"Fallback error: {e2}")
                    # Last resort: show error message
                    error_message = "I'm having trouble processing your request right now. Could you please try rephrasing your question?"
                st.session_state.chat_history.append({"role": "assistant", "content": error_message})
                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                st.rerun()
                return

        # Execute tool calls if any
        if hasattr(response.message, "tool_calls") and response.message.tool_calls:
            print("The response contains the following tool calls: ", response.message.tool_calls)
            st.session_state.chat_history.append({
                "role": "assistant",
                "tool_plan": response.message.tool_plan,
                "tool_calls": response.message.tool_calls,
            })
            # save_chat_history(st.session_state.user["email"], st.session_state.chat_history)

            # Execute tools
            with timer("tool_execution_all"):
                tool_messages = []
                for tc in response.message.tool_calls:
                    try:
                        with timer(f"tool_parsing_{tc.function.name}"):
                            tool_args = json.loads(tc.function.arguments)
                            
                            # Validate that the function exists in our functions_map
                            if tc.function.name not in functions_map:
                                print(f"Unknown function called: {tc.function.name}")
                                continue
                        
                        with timer(f"tool_execution_{tc.function.name}"):
                            tool_result = functions_map[tc.function.name](**tool_args)
                        
                        with timer(f"tool_result_formatting_{tc.function.name}"):
                            if isinstance(tool_result, list):
                                tool_content = [{"type": "document", "document": {"data": json.dumps(data)}} for data in tool_result]
                            else:
                                tool_content = [{"type": "document", "document": {"data": json.dumps(tool_result)}}]
                            tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
                    except Exception as tool_error:
                        print(f"Tool execution error for {tc.function.name}: {tool_error}")
                        # Create error response for this tool call
                        error_content = [{"type": "document", "document": {"data": json.dumps({"status": "error", "message": f"Tool execution failed: {str(tool_error)}"})}}]
                        tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": error_content})
            
            with timer("save_tool_messages"):
                st.session_state.chat_history.extend(tool_messages)
                # save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
            
            # Get final assistant response after tool execution
            try:
                with timer("cohere_api_final_response"):
                    response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
            except Exception as e:
                print(f"Final response error: {e}")
                with timer("cohere_api_final_fallback"):
                    response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history)
            
            # Extract text content properly from final response
            with timer("extract_final_content"):
                final_content = ""
                if hasattr(response.message, "content") and response.message.content:
                    if isinstance(response.message.content, list):
                        for item in response.message.content:
                            if hasattr(item, 'text'):
                                final_content += item.text
                            elif isinstance(item, dict) and 'text' in item:
                                final_content += item['text']
                            elif isinstance(item, str):
                                final_content += item
                    else:
                        if hasattr(response.message.content, 'text'):
                            final_content = response.message.content.text
                        else:
                            final_content = str(response.message.content)
            
            # Only save final response if it has meaningful content
            if final_content and final_content.strip():
                with timer("save_final_response"):
                    st.session_state.chat_history.append({"role": "assistant", "content": final_content})
                    save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
        else:
            # No tool calls - just add the assistant response
            assistant_content = ""
            if hasattr(response.message, "content") and response.message.content:
                if isinstance(response.message.content, list):
                    for item in response.message.content:
                        if hasattr(item, 'text'):
                            assistant_content += item.text
                        elif isinstance(item, dict) and 'text' in item:
                            assistant_content += item['text']
                        elif isinstance(item, str):
                            assistant_content += item
                else:
                    if hasattr(response.message.content, 'text'):
                        assistant_content = response.message.content.text
                    else:
                        assistant_content = str(response.message.content)
            
            # Ensure we have some content to display
            if not assistant_content.strip():
                assistant_content = "I'm here to help! Could you please rephrase your question or provide more details?"
            
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_content})
            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
        
        # Rerun to show the agent's response
        st.rerun()
