
import json
import cohere
from pymongo import MongoClient



client = MongoClient('mongodb://localhost:27017/')
db = client['cohere_mongo']
quizzes_collection = db['quizzes']

# Create the tools
def create_quiz(title: str, questions: list):
    quiz_doc = {"title": title, "questions": questions}
    result = quizzes_collection.insert_one(quiz_doc)
    return {"is_success": True, "message": f"Quiz '{title}' created and stored in MongoDB.", "quiz_id": str(result.inserted_id)}

def search_faqs(query):
    faqs = [
        {"text": "Reimbursing Travel Expenses: Easily manage your travel expenses by submitting them through our finance tool. Approvals are prompt and straightforward."},
        {"text": "Working from Abroad: Working remotely from another country is possible. Simply coordinate with your manager and ensure your availability during core hours."}
    ]
    return  faqs

def search_emails(query):
    emails = [
        {"from": "it@co1t.com", "to": "david@co1t.com", "date": "2024-06-24", "subject": "Setting Up Your IT Needs", "text": "Greetings! To ensure a seamless start, please refer to the attached comprehensive guide, which will assist you in setting up all your work accounts."},
        {"from": "john@co1t.com", "to": "david@co1t.com", "date": "2024-06-24", "subject": "First Week Check-In", "text": "Hello! I hope you're settling in well. Let's connect briefly tomorrow to discuss how your first week has been going. Also, make sure to join us for a welcoming lunch this Thursday at noon—it's a great opportunity to get to know your colleagues!"}
    ]
    return  emails
    
def create_calendar_event(date: str, time: str, duration: int):
    # You can implement any logic here
    return {"is_success": True,
            "message": f"Created a {duration} hour long event at {time} on {date}"}
    


# Define the tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_quiz",
            "description": "Creates a quiz with a title and a list of questions, and stores it in a MongoDB database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the quiz"
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of questions for the quiz"
                    }
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
                    "query": {
                        "type": "string",
                        "description": "The query from the user"
                    }
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
                    "query": {
                        "type": "string",
                        "description": "The query from the user"
                    }
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
                    "date": {
                        "type": "string",
                        "description": "the date on which the event starts, formatted as mm/dd/yy"
                    },
                    "time": {
                        "type": "string",
                        "description": "the time of the event, formatted using 24h military time formatting"
                    },
                    "duration": {
                        "type": "number",
                        "description": "the number of hours the event lasts for"
                    }
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

# Get your free API key: https://dashboard.cohere.com/api-keys

co = cohere.ClientV2(api_key="U2RGL0wY65k9hpjinuZ2MgBq3XWdGCBUryaaqDdG")

# Create custom system message
system_message = """## Task and Context
You are an assistant who assist new employees of Co1t with their first week. You respond to their questions and assist them with their needs. Today is Monday, June 24, 2024"""


# Step 1: Get user message
message = "Generate a quiz about the company culture with 5 questions and store it in the database. The quiz should be titled 'Company Culture Quiz'."

# Add the system and user messages to the chat history
messages = [
    {"role": "system", "content": system_message},
    {"role": "user", "content": message},
]

# Step 2: Tool planning and calling
response = co.chat(model="command-a-03-2025", messages=messages, tools=tools)

if response.message.tool_calls:
    print("Tool plan:")
    print(response.message.tool_plan, "\n")
    print("Tool calls:")
    for tc in response.message.tool_calls:
        print(f"Tool name: {tc.function.name} | Parameters: {tc.function.arguments}")

    # Append tool calling details to the chat history
    messages.append(
        {
            "role": "assistant",
            "tool_calls": response.message.tool_calls,
            "tool_plan": response.message.tool_plan,
        }
    )

# Step 3: Tool execution
for tc in response.message.tool_calls:
    tool_result = functions_map[tc.function.name](**json.loads(tc.function.arguments))
    tool_content = []
    for idx, data in enumerate(tool_result):
        tool_content.append({"type": "document", "document": {"data": json.dumps(data)}})
        # Optional: add an "id" field in the "document" object, otherwise IDs are auto-generated
    # Append tool results to the chat history
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})

print("Tool results:")
for result in tool_content:
    print(result)


# Step 4: Response and citation generation
response = co.chat(
    model="command-a-03-2025",
    messages=messages,
    tools=tools
)

# Append assistant response to the chat history
messages.append({"role": "assistant", "content": response.message.content[0].text})

# Print final response
print("Response:")
print(response.message.content[0].text)
print("="*50)

# Print citations (if any)
if response.message.citations:
    print("\nCITATIONS:")
    for citation in response.message.citations:
        print(citation, "\n")