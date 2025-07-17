import streamlit as st
import cohere
import json
from pymongo import MongoClient

# MongoDB setup (same as in main.py)
client = MongoClient('mongodb://localhost:27017/')
db = client['cohere_mongo']

quizzes_collection = db['quizzes']
users_collection = db['users']


chats_collection = db['chats']
answers_collection = db['answers']

# Helper to serialize chat history for MongoDB
def serialize_chat_history(history):
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

# Cohere setup (same as in main.py)
co = cohere.ClientV2(api_key="7QNs9vQU777ImaYHxonJlNVDrhG9kRLasZ5KloLQ")

# Tool functions (same as in main.py)
def create_quiz(title: str, questions: list):
    quiz_doc = {"title": title, "questions": questions}
    result = quizzes_collection.insert_one(quiz_doc)
    return {"is_success": True, "message": f"Quiz '{title}' created and stored in MongoDB.", "quiz_id": str(result.inserted_id)}

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

# Tool definitions (same as in main.py)
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_quiz",
            "description": "Creates a quiz with a title and a list of questions, and stores it in a MongoDB database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the quiz"},
                    "questions": {"type": "array", "items": {"type": "string"}, "description": "A list of questions for the quiz"}
                },
                "required": ["title", "questions"]
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
    }
]

functions_map = {
    "search_faqs": search_faqs,
    "search_emails": search_emails,
    "create_calendar_event": create_calendar_event,
    "create_quiz": create_quiz
}


# --- LOGIN SECTION ---

st.set_page_config(layout="wide")
if "user" not in st.session_state:
    st.session_state.user = None

# Show user email at top left after login
if st.session_state.user is not None:
    with st.sidebar:
        st.markdown(f"### Hi {st.session_state.user['email']}")
st.title("Cohere Agent Chat")

if st.session_state.user is None:
    tab_login, tab_register = st.tabs(["Login", "Register"])
    with tab_login:
        st.subheader("Login")
        with st.form(key="login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Login")
        if login_submitted:
            user = users_collection.find_one({"email": email})
            if user:
                if user.get("password") == password:
                    st.session_state.user = {"email": email, "name": user.get("name", ""), "age": user.get("age", "")}
                    # Personalized system prompt
                    system_prompt = f"""## Task and Context\nYou are an assistant who assists new employees of Co1t with their first week. You respond to their questions and assist them with their needs. Today is Monday, June 24, 2024.\nThe user's name is {user.get('name', '')} and their age is {user.get('age', '')}. Personalize your responses accordingly."""
                    chat_doc = chats_collection.find_one({"email": email})
                    if chat_doc and "history" in chat_doc:
                        # Update the first system message if needed
                        history = chat_doc["history"]
                        if history and history[0]["role"] == "system":
                            history[0]["content"] = system_prompt
                        else:
                            history = [{"role": "system", "content": system_prompt}] + history
                        st.session_state.chat_history = history
                    else:
                        st.session_state.chat_history = [
                            {"role": "system", "content": system_prompt}
                        ]
                    # Save updated chat history with personalized prompt to MongoDB
                    chats_collection.update_one(
                        {"email": email},
                        {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
                        upsert=True
                    )
                    st.success(f"Welcome, {st.session_state.user['email']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("User not found. Please register.")
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
            user = users_collection.find_one({"email": email})
            if user:
                st.error("User already exists. Please login.")
            else:
                # Validate age is a number
                try:
                    age_int = int(age)
                except ValueError:
                    st.error("Please enter a valid age (number).")
                    st.stop()
                users_collection.insert_one({"email": email, "password": password, "name": name, "age": age_int})
                st.session_state.user = {"email": email, "name": name, "age": age_int}
                # Personalized system prompt
                system_prompt = f"""## Task and Context\nYou are an assistant who assists new employees of Co1t with their first week. You respond to their questions and assist them with their needs. Today is Monday, June 24, 2024.\nThe user's name is {name} and their age is {age_int}. Personalize your responses accordingly."""
                st.session_state.chat_history = [
                    {"role": "system", "content": system_prompt}
                ]
                chats_collection.update_one(
                    {"email": email},
                    {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
                    upsert=True
                )
                st.success(f"Account created. Welcome, {email}!")
                st.rerun()
            st.stop()

# --- END LOGIN SECTION ---

if "chat_history" not in st.session_state:
    # Default system prompt if not logged in
    st.session_state.chat_history = [
        {"role": "system", "content": "## Task and Context\nYou are an assistant who assists new employees of Co1t with their first week. You respond to their questions and assist them with their needs. Today is Monday, June 24, 2024."}
    ]

# Use a form to allow Enter key to send message
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message:", key="user_input", placeholder="Type your message and press Enter")
    submitted = st.form_submit_button("Send")

if submitted and user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    # Save chat history after user message
    if st.session_state.user:
        chats_collection.update_one(
            {"email": st.session_state.user["email"]},
            {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
            upsert=True
        )
    response = co.chat(model="command-a-03-2025", messages=st.session_state.chat_history, tools=tools)

    # Always append the assistant message (with tool calls) right after the user message
    assistant_msg = {"role": "assistant"}
    if hasattr(response.message, "tool_calls") and response.message.tool_calls:
        assistant_msg["tool_calls"] = response.message.tool_calls
        if hasattr(response.message, "tool_plan"):
            assistant_msg["tool_plan"] = response.message.tool_plan
    if hasattr(response.message, "content"):
        # content can be a list or string
        if isinstance(response.message.content, list):
            assistant_msg["content"] = response.message.content
        else:
            assistant_msg["content"] = [response.message.content]
    st.session_state.chat_history.append(assistant_msg)
    # Save chat history after assistant message
    if st.session_state.user:
        chats_collection.update_one(
            {"email": st.session_state.user["email"]},
            {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
            upsert=True
        )

    # If there are tool calls, execute and append tool messages
    if hasattr(response.message, "tool_calls") and response.message.tool_calls:
        tool_messages = []
        for tc in response.message.tool_calls:
            tool_result = functions_map[tc.function.name](**json.loads(tc.function.arguments))
            if isinstance(tool_result, list):
                tool_content = [{"type": "document", "document": {"data": json.dumps(data)}} for data in tool_result]
            else:
                tool_content = [{"type": "document", "document": {"data": json.dumps(tool_result)}}]
            tool_messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
        st.session_state.chat_history.extend(tool_messages)
        # Save chat history after tool messages
        if st.session_state.user:
            chats_collection.update_one(
                {"email": st.session_state.user["email"]},
                {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
                upsert=True
            )
        # Get final assistant response after tool execution
        response = co.chat(model="command-a-03-2025", messages=st.session_state.chat_history, tools=tools)
        st.session_state.chat_history.append({"role": "assistant", "content": response.message.content[0].text})
        # Save chat history after final assistant message
        if st.session_state.user:
            chats_collection.update_one(
                {"email": st.session_state.user["email"]},
                {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
                upsert=True
            )
    elif hasattr(response.message, "content"):
        # If no tool calls, just append the assistant's content
        st.session_state.chat_history.append({"role": "assistant", "content": response.message.content[0].text})
        # Save chat history after assistant message
        if st.session_state.user:
            chats_collection.update_one(
                {"email": st.session_state.user["email"]},
                {"$set": {"history": serialize_chat_history(st.session_state.chat_history)}},
                upsert=True
            )


# Display chat history
for idx, msg in enumerate(st.session_state.chat_history):
    # Only show the last assistant message in a sequence of assistant/tool/assistant after tool calls
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    elif msg["role"] == "assistant":
        # If this assistant message is immediately followed by a tool message and another assistant message, skip this one
        if idx+2 < len(st.session_state.chat_history):
            next_msg = st.session_state.chat_history[idx+1]
            next_next_msg = st.session_state.chat_history[idx+2]
            if next_msg["role"] == "tool" and next_next_msg["role"] == "assistant":
                continue
        # Otherwise, show the assistant message
        st.markdown(f"**Agent:** {msg['content']}")

# --- QUIZ DISPLAY AND ANSWER SECTION ---
# Find the latest quiz in chat history (from tool messages)
latest_quiz = None
latest_quiz_id = None
if st.session_state.user:
    for msg in reversed(st.session_state.chat_history):
        if msg.get("role") == "tool" and msg.get("content"):
            # Try to parse quiz from tool message
            for item in msg["content"]:
                try:
                    data = json.loads(item["document"]["data"])
                    if data.get("quiz_id") and data.get("is_success"):
                        # This is a quiz creation result
                        quiz_id = data["quiz_id"]
                        quiz_doc = db["quizzes"].find_one({"_id": __import__('bson').ObjectId(quiz_id)})
                        if quiz_doc:
                            latest_quiz = quiz_doc
                            latest_quiz_id = quiz_id
                            break
                except Exception:
                    continue
        if latest_quiz:
            break

if latest_quiz and latest_quiz.get("questions"):
    # Only display if all questions are multiple choice with correct answer
    all_mc = all(isinstance(q, dict) and "question" in q and "choices" in q and "answer" in q for q in latest_quiz["questions"])
    if all_mc:
        st.markdown(f"### Quiz: {latest_quiz.get('title','')}")
        quiz_key = f"quiz_{latest_quiz_id}_answers"
        if quiz_key not in st.session_state:
            st.session_state[quiz_key] = [None] * len(latest_quiz["questions"])
        answers = []
        with st.form(key=f"quiz_form_{latest_quiz_id}"):
            for i, q in enumerate(latest_quiz["questions"]):
                ans = st.radio(q["question"], q["choices"], key=f"quiz_{latest_quiz_id}_q{i}")
                answers.append(ans)
            submitted = st.form_submit_button("Submit Quiz Answers")
            if submitted:
                # Save answers to answers_collection
                answers_collection.update_one(
                    {"user_email": st.session_state.user["email"], "quiz_id": latest_quiz_id},
                    {"$set": {"answers": answers}},
                    upsert=True
                )
                # Compare answers to correct ones
                correct = 0
                for i, q in enumerate(latest_quiz["questions"]):
                    if answers[i] == q["answer"]:
                        correct += 1
                st.success(f"Your answers have been recorded! You got {correct} out of {len(latest_quiz['questions'])} correct.")
