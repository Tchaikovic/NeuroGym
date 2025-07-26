#!/usr/bin/env python3
"""
Test script for Cohere chat interface
This script tests the Cohere API integration separately from the Streamlit app
"""

import json
import sys
import traceback
from datetime import datetime

try:
    import cohere
    from config import COHERE_API_KEY, COHERE_MODEL
    print("✅ Successfully imported Cohere and config")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have cohere installed: pip install cohere")
    sys.exit(1)

# Initialize Cohere client
try:
    co = cohere.ClientV2(api_key=COHERE_API_KEY)
    print(f"✅ Cohere client initialized with model: {COHERE_MODEL}")
except Exception as e:
    print(f"❌ Failed to initialize Cohere client: {e}")
    sys.exit(1)

# Tool definitions (same as in the main app)
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

def extract_text_content(content):
    """Extract text content from Cohere response"""
    if not content:
        return ""
    
    if isinstance(content, str):
        return content
    
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
    
    if hasattr(content, 'text'):
        return content.text
    
    return str(content)

def test_basic_chat():
    """Test basic chat without tools"""
    print("\n🧪 Testing basic chat (no tools)...")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI tutor."},
        {"role": "user", "content": "Hello! How are you today?"}
    ]
    
    try:
        response = co.chat(model=COHERE_MODEL, messages=messages)
        content = extract_text_content(response.message.content)
        print(f"✅ Basic chat successful!")
        print(f"   Response: {content[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Basic chat failed: {e}")
        traceback.print_exc()
        return False

def test_chat_with_tools():
    """Test chat with tools enabled"""
    print("\n🧪 Testing chat with tools...")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI tutor. Only use tools when explicitly requested."},
        {"role": "user", "content": "I want to learn about Python programming"}
    ]
    
    try:
        response = co.chat(model=COHERE_MODEL, messages=messages, tools=tools)
        content = extract_text_content(response.message.content)
        
        print(f"✅ Chat with tools successful!")
        print(f"   Response: {content[:100]}...")
        
        if hasattr(response.message, "tool_calls") and response.message.tool_calls:
            print(f"   🔧 Tool calls detected: {len(response.message.tool_calls)}")
            for i, tc in enumerate(response.message.tool_calls):
                print(f"      Tool {i+1}: {tc.function.name}")
                print(f"      Args: {tc.function.arguments}")
        else:
            print(f"   📝 No tool calls (normal conversation)")
        
        return True
    except Exception as e:
        print(f"❌ Chat with tools failed: {e}")
        traceback.print_exc()
        return False

def test_quiz_request():
    """Test explicit quiz request"""
    print("\n🧪 Testing explicit quiz request...")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI tutor. Only use tools when explicitly requested."},
        {"role": "user", "content": "Can you create a quiz about Python basics?"}
    ]
    
    try:
        response = co.chat(model=COHERE_MODEL, messages=messages, tools=tools)
        content = extract_text_content(response.message.content)
        
        print(f"✅ Quiz request successful!")
        print(f"   Response: {content[:100]}...")
        
        if hasattr(response.message, "tool_calls") and response.message.tool_calls:
            print(f"   🔧 Tool calls detected: {len(response.message.tool_calls)}")
            for i, tc in enumerate(response.message.tool_calls):
                print(f"      Tool {i+1}: {tc.function.name}")
                if tc.function.name == "create_quiz":
                    args = json.loads(tc.function.arguments)
                    print(f"      Quiz title: {args.get('title', 'N/A')}")
                    print(f"      Topic: {args.get('topic', 'N/A')}")
                    print(f"      Difficulty: {args.get('difficulty', 'N/A')}")
                    print(f"      Questions: {len(args.get('questions', []))}")
        else:
            print(f"   ⚠️  No tool calls detected (expected create_quiz)")
        
        return True
    except Exception as e:
        print(f"❌ Quiz request failed: {e}")
        traceback.print_exc()
        return False

def test_conversation_flow():
    """Test a multi-turn conversation"""
    print("\n🧪 Testing conversation flow...")
    
    conversation = [
        {"role": "system", "content": "You are a helpful AI tutor. Only use tools when explicitly requested."},
        {"role": "user", "content": "Hi there!"},
    ]
    
    try:
        # Turn 1: Basic greeting
        response1 = co.chat(model=COHERE_MODEL, messages=conversation)
        content1 = extract_text_content(response1.message.content)
        conversation.append({"role": "assistant", "content": content1})
        
        print(f"   Turn 1 - User: Hi there!")
        print(f"   Turn 1 - Assistant: {content1[:100]}...")
        
        # Turn 2: Topic interest
        conversation.append({"role": "user", "content": "I'm interested in learning math"})
        response2 = co.chat(model=COHERE_MODEL, messages=conversation, tools=tools)
        content2 = extract_text_content(response2.message.content)
        
        print(f"   Turn 2 - User: I'm interested in learning math")
        print(f"   Turn 2 - Assistant: {content2[:100]}...")
        
        if hasattr(response2.message, "tool_calls") and response2.message.tool_calls:
            print(f"   🔧 Tool calls in turn 2: {len(response2.message.tool_calls)}")
            for tc in response2.message.tool_calls:
                print(f"      Tool: {tc.function.name}")
        
        print(f"✅ Conversation flow test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Conversation flow failed: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling with problematic inputs"""
    print("\n🧪 Testing error handling...")
    
    test_cases = [
        # Test with empty message
        [],
        # Test with malformed message
        [{"role": "user"}],
        # Test with very long message
        [{"role": "user", "content": "A" * 10000}]
    ]
    
    for i, messages in enumerate(test_cases):
        try:
            response = co.chat(model=COHERE_MODEL, messages=messages)
            print(f"   Test case {i+1}: Handled gracefully")
        except Exception as e:
            print(f"   Test case {i+1}: Error - {type(e).__name__}: {str(e)[:100]}")
    
    print(f"✅ Error handling test completed!")
    return True

def interactive_test():
    """Interactive testing mode"""
    print("\n🎮 Interactive test mode - Type 'quit' to exit")
    
    conversation = [
        {"role": "system", "content": "You are a helpful AI tutor. Only use tools when explicitly requested."}
    ]
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            conversation.append({"role": "user", "content": user_input})
            
            # Decide whether to use tools based on keywords
            use_tools = any(keyword in user_input.lower() for keyword in 
                          ["quiz", "test", "create", "topic", "learn", "study"])
            
            if use_tools:
                response = co.chat(model=COHERE_MODEL, messages=conversation, tools=tools)
            else:
                response = co.chat(model=COHERE_MODEL, messages=conversation)
            
            content = extract_text_content(response.message.content)
            print(f"AI: {content}")
            
            conversation.append({"role": "assistant", "content": content})
            
            # Show tool calls if any
            if hasattr(response.message, "tool_calls") and response.message.tool_calls:
                print(f"🔧 Tool calls: {[tc.function.name for tc in response.message.tool_calls]}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Cohere Chat Interface Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Basic Chat", test_basic_chat),
        ("Chat with Tools", test_chat_with_tools),
        ("Quiz Request", test_quiz_request),
        ("Conversation Flow", test_conversation_flow),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cohere integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    # Offer interactive mode
    if input("\n🎮 Run interactive test? (y/n): ").lower().startswith('y'):
        interactive_test()

if __name__ == "__main__":
    main()
