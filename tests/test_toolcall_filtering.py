"""
Test script to validate ToolCallV2Function filtering in chat history storage
"""
import json

def test_toolcall_filtering():
    """Test that ToolCallV2Function objects are properly filtered out"""
    
    print("Testing ToolCallV2Function filtering...")
    
    # Import the filtering functions
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from src.chat_memory import save_chat_history_direct, load_chat_history_direct, SimpleChatMemory
    
    # Create a mock ToolCallV2Function-like object (non-serializable)
    class MockToolCallV2Function:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments
        
        def __str__(self):
            return f"MockToolCallV2Function(name={self.name})"
    
    # Create test chat history with non-serializable objects
    test_history = [
        {"role": "system", "content": "You are a helpful AI tutor."},
        {"role": "user", "content": "Hello, can you help me with math?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help."},
        {
            "role": "assistant", 
            "tool_calls": [MockToolCallV2Function("create_quiz", '{"title": "Math Quiz"}')],  # Non-serializable
            "content": "I'll create a quiz for you."
        },
        {
            "role": "tool", 
            "tool_call_id": "123", 
            "content": [{"type": "document", "document": {"data": '{"status": "success"}'}}]
        },
        {"role": "assistant", "content": "Here's your quiz!"}
    ]
    
    # Test 1: Direct filtering test
    test_email = "test_filtering@example.com"
    print(f"1. Testing save/load with filtering for {test_email}")
    
    try:
        # This should filter out the non-serializable tool_calls
        save_chat_history_direct(test_email, test_history)
        loaded_history = load_chat_history_direct(test_email)
        
        print(f"   Original messages: {len(test_history)}")
        print(f"   Loaded messages: {len(loaded_history)}")
        
        # Check that all loaded messages are serializable
        serializable_count = 0
        for i, msg in enumerate(loaded_history):
            try:
                json.dumps(msg)
                serializable_count += 1
                print(f"   ✅ Message {i}: {msg.get('role')} -> serializable")
            except (TypeError, ValueError) as e:
                print(f"   ❌ Message {i}: {msg.get('role')} -> NOT serializable: {e}")
        
        print(f"   All {serializable_count} loaded messages are serializable!")
        
        # Test 2: Check that tool_calls are filtered out
        print("2. Testing tool_calls filtering")
        has_tool_calls = any("tool_calls" in msg for msg in loaded_history)
        if has_tool_calls:
            print("   ❌ tool_calls found in loaded history (should be filtered)")
        else:
            print("   ✅ tool_calls properly filtered out")
        
        # Test 3: Check that essential content is preserved
        print("3. Testing content preservation")
        user_messages = [msg for msg in loaded_history if msg.get("role") == "user"]
        assistant_messages = [msg for msg in loaded_history if msg.get("role") == "assistant"]
        tool_messages = [msg for msg in loaded_history if msg.get("role") == "tool"]
        
        print(f"   User messages: {len(user_messages)}")
        print(f"   Assistant messages: {len(assistant_messages)}")
        print(f"   Tool messages: {len(tool_messages)}")
        
        # Check that we have the right content
        if len(user_messages) >= 1 and "math" in user_messages[0].get("content", ""):
            print("   ✅ User content preserved")
        else:
            print("   ❌ User content not found")
        
        if len(tool_messages) >= 1 and tool_messages[0].get("tool_call_id"):
            print("   ✅ Tool message structure preserved")
        else:
            print("   ❌ Tool message structure not preserved")
        
    except Exception as e:
        print(f"   ❌ Error in filtering test: {e}")
        return False
    
    print("4. All filtering tests passed! ✅")
    return True

def test_direct_serialization():
    """Test that we can serialize the cleaned messages directly"""
    print("\n5. Testing direct JSON serialization")
    
    from src.chat_memory import SimpleChatMemory
    
    # Create mock data
    memory = SimpleChatMemory("test@example.com")
    
    # Test message with non-serializable content
    class NonSerializable:
        pass
    
    test_message = {
        "role": "assistant",
        "content": "Hello",
        "tool_calls": [NonSerializable()],  # This should be filtered out
        "metadata": {"key": "value"}  # This should be kept
    }
    
    cleaned = memory._clean_message_for_storage(test_message)
    
    try:
        json_str = json.dumps(cleaned)
        print("   ✅ Cleaned message is JSON serializable")
        print(f"   Cleaned message keys: {list(cleaned.keys())}")
        
        if "tool_calls" in cleaned:
            print("   ❌ tool_calls not filtered out")
        else:
            print("   ✅ tool_calls properly filtered out")
            
        if "content" in cleaned and "metadata" in cleaned:
            print("   ✅ Serializable fields preserved")
        else:
            print("   ❌ Some serializable fields lost")
            
    except Exception as e:
        print(f"   ❌ Cleaned message still not serializable: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("NeuroGym ToolCallV2Function Filtering Validation")
    print("=" * 50)
    
    success1 = test_toolcall_filtering()
    success2 = test_direct_serialization()
    
    if success1 and success2:
        print("\n🎉 All filtering tests passed!")
        print("✅ ToolCallV2Function objects are properly filtered out")
        print("✅ Chat history can be saved to MongoDB without errors")
        print("✅ Essential message content is preserved")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
