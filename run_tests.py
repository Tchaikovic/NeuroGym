#!/usr/bin/env python3
"""
Test runner for NeuroGym AI Tutor tests
Run all tests from the project root directory
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_all_tests():
    """Run all available tests"""
    print("🧪 NeuroGym AI Tutor - Test Suite")
    print("=" * 50)
    
    # Import and run individual test modules
    test_modules = [
        'tests.test_toolcall_filtering',
        'tests.test_direct_storage',
    ]
    
    success_count = 0
    total_count = len(test_modules)
    
    for module_name in test_modules:
        try:
            print(f"\n🔍 Running {module_name}...")
            
            if module_name == 'tests.test_toolcall_filtering':
                from tests.test_toolcall_filtering import test_toolcall_filtering, test_direct_serialization
                test_toolcall_filtering()
                test_direct_serialization()
                
            elif module_name == 'tests.test_direct_storage':
                from tests.test_direct_storage import test_direct_storage
                test_direct_storage()
            
            print(f"✅ {module_name} - PASSED")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {module_name} - FAILED: {e}")
    
    print(f"\n📊 Test Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed!")
        return False

if __name__ == "__main__":
    run_all_tests()
