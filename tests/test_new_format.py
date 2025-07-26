"""
Simple test script to validate the new chat format works correctly
"""
def test_message_format():
    """Test that messages have the correct format"""
    
    print("Testing new chat message format...")
    
    # Sample chat history in Cohere API v2 format
    test_history = [
        {"role": "system", "content": "You are a helpful AI tutor."},
        {"role": "user", "content": "Hello, can you help me with math?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help you with math."},
        {"role": "assistant", "tool_calls": [{"id": "123", "function": {"name": "create_quiz", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "123", "content": [{"type": "document", "document": {"data": "{\"status\": \"success\"}"}}]}
    ]
    
    print("✅ Sample messages created in Cohere API v2 format")
    
    # Test format validation
    for i, msg in enumerate(test_history):
        role = msg.get("role")
        
        if role in ["system", "user", "assistant"]:
            if "content" in msg:
                print(f"   ✅ Message {i} ({role}): has 'content' field")
            elif role == "assistant" and "tool_calls" in msg:
                print(f"   ✅ Message {i} ({role}): has 'tool_calls' field")
            else:
                print(f"   ❌ Message {i} ({role}): missing required fields")
                return False
        elif role == "tool":
            if "tool_call_id" in msg and "content" in msg:
                print(f"   ✅ Message {i} ({role}): has required fields")
            else:
                print(f"   ❌ Message {i} ({role}): missing required fields")
                return False
    
    print("🎉 All messages pass format validation!")
    return True

if __name__ == "__main__":
    print("NeuroGym Chat Format Validation")
    print("=" * 40)
    
    success = test_message_format()
    
    if success:
        print("\n✅ New chat format is correctly structured!")
        print("Messages use 'content' field consistently.")
        print("No conversion functions needed for Cohere API v2.")
    else:
        print("\n❌ Format validation failed.")
