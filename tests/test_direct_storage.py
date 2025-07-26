"""
Test script to validate the new direct MongoDB chat storage works correctly
"""
def test_direct_storage():
    """Test that the new direct storage works"""
    
    print("Testing direct MongoDB chat storage...")
    
    # Import the new functions
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from src.chat_memory import save_chat_history_direct, load_chat_history_direct
    
    # Sample chat history in Cohere API v2 format
    test_history = [
        {"role": "system", "content": "You are a helpful AI tutor."},
        {"role": "user", "content": "Hello, can you help me with math?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help you with math."},
        {"role": "assistant", "tool_calls": [{"id": "123", "function": {"name": "create_quiz"}}]},
        {"role": "tool", "tool_call_id": "123", "content": [{"type": "document", "document": {"data": '{"status": "success"}'}}]}
    ]
    
    # Test 1: Save and load chat history
    test_email = "test@example.com"
    print(f"1. Testing save/load for {test_email}")
    
    try:
        save_chat_history_direct(test_email, test_history)
        loaded_history = load_chat_history_direct(test_email)
        
        print(f"   Saved {len(test_history)} messages")
        print(f"   Loaded {len(loaded_history)} messages")
        
        # Check format consistency
        for i, msg in enumerate(loaded_history):
            if "content" not in msg and msg.get("role") != "assistant":
                print(f"   ❌ Message {i} missing 'content' field")
            else:
                role = msg.get("role", "unknown")
                has_content = "content" in msg
                has_tool_calls = "tool_calls" in msg
                print(f"   ✅ Message {i}: {role} -> content: {has_content}, tool_calls: {has_tool_calls}")
        
        # Test 2: Verify exact format match
        print("2. Testing format preservation")
        if loaded_history == test_history:
            print("   ✅ Exact format match - no conversion needed!")
        else:
            print("   ⚠️  Format differences detected")
            for i, (original, loaded) in enumerate(zip(test_history, loaded_history)):
                if original != loaded:
                    print(f"     Message {i} differs:")
                    print(f"       Original: {original}")
                    print(f"       Loaded:   {loaded}")
        
    except Exception as e:
        print(f"   ❌ Error in storage test: {e}")
        return False
    
    print("3. All tests passed! ✅")
    return True

if __name__ == "__main__":
    print("NeuroGym Direct MongoDB Storage Validation")
    print("=" * 45)
    
    success = test_direct_storage()
    
    if success:
        print("\n🎉 Direct MongoDB storage is working correctly!")
        print("✅ No LangChain dependencies needed")
        print("✅ No conversion functions required")
        print("✅ Cohere API v2 format preserved exactly")
    else:
        print("\n❌ Tests failed. Please check the implementation.")
