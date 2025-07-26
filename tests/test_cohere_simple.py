#!/usr/bin/env python3
"""
Simple Cohere API test script
Tests basic API connectivity and functionality
"""

import json
import sys
import os

def test_config():
    """Test if config is accessible"""
    try:
        from config import COHERE_API_KEY, COHERE_MODEL
        print(f"✅ Config loaded successfully")
        print(f"   Model: {COHERE_MODEL}")
        print(f"   API Key: {'*' * 20}...{COHERE_API_KEY[-4:] if len(COHERE_API_KEY) > 4 else '****'}")
        return True
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False

def test_cohere_import():
    """Test if Cohere can be imported"""
    try:
        import cohere
        print(f"✅ Cohere library imported successfully")
        print(f"   Version: {cohere.__version__ if hasattr(cohere, '__version__') else 'Unknown'}")
        return True
    except ImportError as e:
        print(f"❌ Cohere import failed: {e}")
        print("   Install with: pip install cohere")
        return False

def simple_api_test():
    """Simple API connectivity test"""
    try:
        import cohere
        from config import COHERE_API_KEY, COHERE_MODEL
        
        co = cohere.ClientV2(api_key=COHERE_API_KEY)
        
        # Simple test message
        messages = [{"role": "user", "content": "Hello, can you say hi back?"}]
        
        response = co.chat(model=COHERE_MODEL, messages=messages)
        
        # Extract response content
        content = ""
        if hasattr(response.message, "content"):
            if isinstance(response.message.content, list):
                for item in response.message.content:
                    if hasattr(item, 'text'):
                        content += item.text
                    elif isinstance(item, dict) and 'text' in item:
                        content += item['text']
                    elif isinstance(item, str):
                        content += item
            elif hasattr(response.message.content, 'text'):
                content = response.message.content.text
            else:
                content = str(response.message.content)
        
        print(f"✅ API test successful!")
        print(f"   Response: {content[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Run basic tests"""
    print("🔍 Simple Cohere API Test")
    print("=" * 40)
    
    tests = [
        ("Config Load", test_config),
        ("Cohere Import", test_cohere_import),
        ("API Connectivity", simple_api_test)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
        
        if not results[-1]:
            print("⚠️  Stopping tests due to failure")
            break
    
    print("\n" + "=" * 40)
    print("📊 SUMMARY")
    print("=" * 40)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 All tests passed! Basic setup is working.")
        print("\n💡 You can now run the full test with: python test_cohere.py")
    else:
        print(f"❌ {total - passed} test(s) failed.")
        print("\n🔧 Please fix the issues above before proceeding.")

if __name__ == "__main__":
    main()
