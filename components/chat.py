"""
Chat page - handles the main chat interface with AI tutor
"""
import streamlit as st
import json
import cohere
from database import (
    load_chat_history, save_chat_history, store_topic, 
    get_quiz_by_id, save_quiz_answers, db, get_user_topics, count_user_messages
)
from config import COHERE_API_KEY, COHERE_MODEL, TUTOR_SYSTEM_PROMPT

# Cohere setup
co = cohere.ClientV2(api_key=COHERE_API_KEY)

# Tool functions
def create_quiz(title: str, questions: list, difficulty: str = "medium", topic: str = None):
    """Create a quiz with title, questions, difficulty, and topic"""
    from database import quizzes_collection, topics_collection
    import re
    from difflib import SequenceMatcher
    
    # Each question must be a dict with 'question', 'choices', and 'answer'
    formatted_questions = []
    invalid_questions = []
    for q in questions:
        if isinstance(q, dict) and all(k in q for k in ["question", "choices", "answer"]):
            formatted_questions.append(q)
        else:
            invalid_questions.append(q)
    if not formatted_questions:
        return {"is_success": False, "message": "No valid questions provided. Each question must be a dict with 'question', 'choices', and 'answer'.", "invalid_questions": invalid_questions}
    
    # Find topic_id for the current user and topic
    topic_id = None
    user_email = None
    
    # Try to get user email from session state
    try:
        if hasattr(st, 'session_state') and st.session_state.user:
            user_email = st.session_state.user["email"]
    except:
        pass
    
    # Function to normalize topic strings for similarity comparison
    def normalize_topic(topic_str):
        if not topic_str:
            return ""
        # Convert to lowercase, remove extra spaces, punctuation
        normalized = re.sub(r'[^\w\s]', '', topic_str.lower().strip())
        # Remove common words that don't add semantic value
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'basics', 'fundamentals', 'introduction', 'intro'}
        words = [word for word in normalized.split() if word not in common_words]
        return ' '.join(sorted(words))  # Sort words to handle different word orders
    
    # Function to calculate similarity between two topics
    def topics_are_similar(topic1, topic2, threshold=0.8):
        norm1 = normalize_topic(topic1)
        norm2 = normalize_topic(topic2)
        if not norm1 or not norm2:
            return False
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold
    
    # If we have both topic and user email, find or create the topic
    if topic and user_email:
        # Get all existing topics for this user
        existing_topics = list(topics_collection.find({"user_email": user_email}))
        
        # Check for semantic similarity with existing topics
        similar_topic = None
        for existing_topic in existing_topics:
            if topics_are_similar(topic, existing_topic.get("topic", "")):
                similar_topic = existing_topic
                break
        
        if similar_topic:
            # Use the existing similar topic
            topic_id = str(similar_topic.get("_id"))
            topic = similar_topic.get("topic")  # Use the existing topic name
        else:
            # Create new topic as no similar one exists
            topic_result = topics_collection.insert_one({
                "user_email": user_email,
                "topic": topic,
                "date": __import__('datetime').datetime.now().isoformat()
            })
            topic_id = str(topic_result.inserted_id)
    
    quiz_doc = {
        "title": title,
        "questions": formatted_questions,
        "difficulty": difficulty,
        "topic_id": topic_id,
        "topic": topic
    }
    result = quizzes_collection.insert_one(quiz_doc)
    msg = f"Quiz '{title}' created and stored in MongoDB."
    if invalid_questions:
        msg += f" Some questions were skipped due to invalid format: {invalid_questions}"
    return {"is_success": True, "message": msg, "quiz_id": str(result.inserted_id)}

def search_faqs(query):
    faqs = [
        {"text": "Reimbursing Travel Expenses: Easily manage your travel expenses by submitting them through our finance tool. Approvals are prompt and straightforward."},
        {"text": "Working from Abroad: Working remotely from another country is possible. Simply coordinate with your manager and ensure your availability during core hours."}
    ]
    return faqs

def search_emails(query):
    emails = [
        {"from": "it@co1t.com", "to": "david@co1t.com", "date": "2024-06-24", "subject": "Setting Up Your IT Needs", "text": "Greetings! To ensure a seamless start, please refer to the attached comprehensive guide, which will assist you in setting up all your work accounts."},
        {"from": "john@co1t.com", "to": "david@co1t.com", "date": "2024-06-24", "subject": "First Week Check-In", "text": "Hello! I hope you're settling in well. Let's connect briefly tomorrow to discuss how your first week has been going. Also, make sure to join us for a welcoming lunch this Thursday at noon—it's a great opportunity to get to know your colleagues!"}
    ]
    return emails

def create_calendar_event(date: str, time: str, duration: int):
    return {"is_success": True,
            "message": f"Created a {duration} hour long event at {time} on {date}"}

def suggest_topics(user_email: str = None):
    """Suggest existing topics or prompt for new topic selection"""
    try:
        if hasattr(st, 'session_state') and st.session_state.user:
            user_email = st.session_state.user["email"]
            existing_topics = get_user_topics(user_email)
            
            if existing_topics:
                topic_list = [topic_doc['topic'] for topic_doc in existing_topics]
                return {
                    "is_success": True,
                    "message": f"I see you've worked on these topics before: {', '.join(topic_list)}. Would you like to continue with one of these or start a new topic?",
                    "existing_topics": topic_list
                }
            else:
                return {
                    "is_success": True,
                    "message": "What topic would you like to work on? I can help with any subject you're studying!",
                    "existing_topics": []
                }
    except Exception as e:
        return {"is_success": False, "message": "Unable to retrieve topics", "error": str(e)}

# Tool definitions for Cohere
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_quiz",
            "description": "Creates a quiz with a title, topic, difficulty, and a list of questions, and stores it in a MongoDB database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the quiz"},
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "choices": {"type": "array", "items": {"type": "string"}},
                                "answer": {"type": "string"}
                            },
                            "required": ["question", "choices", "answer"]
                        },
                        "description": "A list of multiple choice questions for the quiz"
                    },
                    "difficulty": {"type": "string", "description": "The difficulty level assigned by the agent (e.g., easy, medium, hard)"},
                    "topic": {"type": "string", "description": "The topic for the quiz, as identified by the student"}
                },
                "required": ["title", "questions", "difficulty", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_faqs",
            "description": "Given a user query, searches a company's frequently asked questions (FAQs) list and returns the most relevant matches to the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query from the user"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Given a user query, searches a person's emails and returns the most relevant matches to the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query from the user"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Creates a new calendar event of the specified duration at the specified time and date. A new event cannot be created on the same time as an existing event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "the date on which the event starts, formatted as mm/dd/yy"},
                    "time": {"type": "string", "description": "the time of the event, formatted using 24h military time formatting"},
                    "duration": {"type": "number", "description": "the number of hours the event lasts for"}
                },
                "required": ["date", "time", "duration"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_topics",
            "description": "Suggest existing topics or prompt for new topic selection when the student is ready to start learning",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_email": {"type": "string", "description": "The user's email (optional, will be auto-filled)"}
                },
                "required": []
            }
        }
    }
]

# Map function names to Python functions for tool execution
functions_map = {
    "search_faqs": search_faqs,
    "search_emails": search_emails,
    "create_calendar_event": create_calendar_event,
    "create_quiz": create_quiz,
    "suggest_topics": suggest_topics
}

def render_quiz_inline(msg):
    """Render quiz inline within chat history"""
    if msg.get("content"):
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
                                    # Show choices as radio buttons with answer text
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

def show_chat():
    """Display the main chat interface"""
    # Ensure chat history exists for logged-in users
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
            st.session_state.chat_history = [{"role": "system", "content": system_prompt}]

    # Display chat history
    for idx, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            # Skip assistant message if followed by tool message and another assistant message
            if idx+2 < len(st.session_state.chat_history):
                next_msg = st.session_state.chat_history[idx+1]
                next_next_msg = st.session_state.chat_history[idx+2]
                if next_msg["role"] == "tool" and next_next_msg["role"] == "assistant":
                    continue
            
            # Skip assistant message if followed by a tool message that contains a quiz
            should_skip = False
            if idx+1 < len(st.session_state.chat_history):
                next_msg = st.session_state.chat_history[idx+1]
                if next_msg["role"] == "tool" and next_msg.get("content"):
                    # Check if this tool message contains a quiz
                    for item in next_msg["content"]:
                        try:
                            data = json.loads(item["document"]["data"])
                            if data.get("quiz_id") and data.get("is_success"):
                                should_skip = True
                                break
                        except:
                            pass
            
            # Also skip if this assistant message appears to contain quiz content
            # (This handles the final assistant response after quiz tool execution)
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
            
            # Check if content contains quiz patterns (multiple choice questions)
            if content and isinstance(content, str):
                # Look for patterns that indicate this is a quiz text representation
                # But exclude feedback messages that start with "Your answers have been recorded"
                is_feedback = content.startswith("Your answers have been recorded")
                
                if not is_feedback:
                    quiz_indicators = [
                        "What is" in content and "?" in content and len(content.split("?")) > 2,
                        "quiz" in content.lower() and ("a)" in content.lower() or "1)" in content.lower() or "•" in content),
                        content.count("?") >= 3 and any(choice in content for choice in ["A.", "B.", "C.", "D.", "1.", "2.", "3.", "4."]),
                        "Take your time and let me know your answers" in content
                    ]
                    if any(quiz_indicators):
                        should_skip = True
            
            if should_skip:
                continue
            
            # Extract text content properly for display
            if isinstance(msg.get('content', ''), list):
                # Handle list of content items (Cohere response format)
                text_content = ""
                for item in msg['content']:
                    if hasattr(item, 'text'):
                        text_content += item.text
                    elif isinstance(item, dict) and 'text' in item:
                        text_content += item['text']
                    elif isinstance(item, str):
                        text_content += item
                content = text_content
            elif hasattr(msg.get('content', ''), 'text'):
                # Handle single content item with text attribute
                content = msg['content'].text
            else:
                content = str(msg.get('content', ''))
            
            # Ensure we have content to display
            if not content.strip():
                content = "[No response content]"
            
            st.markdown(f"**Agent:** {content}")
        elif msg["role"] == "tool" and msg.get("content") and st.session_state.user:
            # Render quiz inline
            render_quiz_inline(msg)

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
                            response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
                            
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
                                    tool_args = json.loads(tc.function.arguments)
                                    tool_result = functions_map[tc.function.name](**tool_args)
                                    
                                    if isinstance(tool_result, list):
                                        tool_content = [{"type": "document", "document": {"data": json.dumps(data)}} for data in tool_result]
                                    else:
                                        tool_content = [{"type": "document", "document": {"data": json.dumps(tool_result)}}]
                                    tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
                                
                                st.session_state.chat_history.extend(tool_messages)
                                save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
                                
                                # Get final assistant response after tool execution
                                response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
                                
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
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Check if this looks like a topic selection (after some conversation)
        user_msgs = [m for m in st.session_state.chat_history if m["role"] == "user"]
        if len(user_msgs) >= 2:
            # Simple heuristics to detect topic mention
            topic_keywords = ["work on", "study", "learn", "help with", "struggling with", "need help", "practice"]
            if any(keyword in user_input.lower() for keyword in topic_keywords) or len(user_msgs) >= 3:
                # Try to extract topic from the message
                # For now, store the whole message as potential topic - the AI will handle topic extraction
                pass  # We'll let the AI handle topic extraction through tools
        
        # Save chat history after user message
        save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
        
        # Get AI response
        response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)

        # Execute tool calls if any
        if hasattr(response.message, "tool_calls") and response.message.tool_calls:
            # Process assistant message with tool calls
            assistant_msg = {"role": "assistant"}
            assistant_msg["tool_calls"] = response.message.tool_calls
            if hasattr(response.message, "tool_plan"):
                assistant_msg["tool_plan"] = response.message.tool_plan
            
            # Extract text content properly
            assistant_content = ""
            if hasattr(response.message, "content") and response.message.content:
                if isinstance(response.message.content, list):
                    # Extract text from list of content items
                    for item in response.message.content:
                        if hasattr(item, 'text'):
                            assistant_content += item.text
                        elif isinstance(item, dict) and 'text' in item:
                            assistant_content += item['text']
                        elif isinstance(item, str):
                            assistant_content += item
                else:
                    # Handle single content item
                    if hasattr(response.message.content, 'text'):
                        assistant_content = response.message.content.text
                    else:
                        assistant_content = str(response.message.content)
            
            assistant_msg["content"] = assistant_content
            st.session_state.chat_history.append(assistant_msg)
            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
            
            # Execute tools
            tool_messages = []
            for tc in response.message.tool_calls:
                tool_args = json.loads(tc.function.arguments)
                tool_result = functions_map[tc.function.name](**tool_args)
                
                if isinstance(tool_result, list):
                    tool_content = [{"type": "document", "document": {"data": json.dumps(data)}} for data in tool_result]
                else:
                    tool_content = [{"type": "document", "document": {"data": json.dumps(tool_result)}}]
                tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
            
            st.session_state.chat_history.extend(tool_messages)
            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
            
            # Get final assistant response after tool execution
            response = co.chat(model=COHERE_MODEL, messages=st.session_state.chat_history, tools=tools)
            
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
            
            # Ensure we have some content to display
            if not assistant_content.strip():
                assistant_content = "I'm here to help! Could you please rephrase your question or provide more details?"
            
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_content})
            save_chat_history(st.session_state.user["email"], st.session_state.chat_history)
        
        # Rerun to show the agent's response
        st.rerun()
