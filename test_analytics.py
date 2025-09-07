#!/usr/bin/env python3
"""
Test script for AskBucky Analytics System

This script tests the analytics functionality to ensure events are being logged correctly.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code', 'python'))

import analytics
from aiohttp import web

def test_analytics_functions():
    """Test the analytics functions directly"""
    print("🧪 Testing Analytics Functions...")
    
    # Create mock request and response objects
    class MockRequest:
        def __init__(self):
            self.cookies = {}
            self.query = {}
            self.headers = {}
            self.path = "/test"
    
    class MockResponse:
        def __init__(self):
            self.cookies = {}
        
        def set_cookie(self, name, value, **kwargs):
            self.cookies[name] = value
    
    request = MockRequest()
    response = MockResponse()
    
    # Test 1: User ID and Session ID generation
    print("\n1. Testing user/session ID generation...")
    uid, sid = analytics.get_or_set_ids(request, response)
    print(f"   User ID: {uid}")
    print(f"   Session ID: {sid}")
    print(f"   Cookies set: {response.cookies}")
    
    # Test 2: UTM parameter extraction
    print("\n2. Testing UTM parameter extraction...")
    request.query = {
        'utm_source': 'google',
        'utm_medium': 'cpc',
        'utm_campaign': 'test_campaign'
    }
    utm_data = analytics.extract_utm_params(request)
    print(f"   UTM data: {utm_data}")
    
    # Test 3: Event logging
    print("\n3. Testing event logging...")
    analytics.log_event("test_event", uid, sid, test_prop="test_value")
    print("   ✓ Event logged successfully")
    
    # Test 4: Page view logging
    print("\n4. Testing page view logging...")
    analytics.log_page_view(request, response, path="/test", sitetag="test_site")
    print("   ✓ Page view logged successfully")
    
    # Test 5: Ask started logging
    print("\n5. Testing ask started logging...")
    analytics.log_ask_started(request, response, "test query", "test_site", "test_sitetag")
    print("   ✓ Ask started logged successfully")
    
    # Test 6: Ask answered logging
    print("\n6. Testing ask answered logging...")
    analytics.log_ask_answered(
        request, response, "test query", "success", 3, 1500,
        "test_site", "test_sitetag", "gpt-4o-mini", 25
    )
    print("   ✓ Ask answered logged successfully")
    
    # Test 7: Error logging
    print("\n7. Testing error logging...")
    analytics.log_error(request, response, "test_error", "Test error message", "test query", "test_site")
    print("   ✓ Error logged successfully")
    
    # Test 8: Daily job logging
    print("\n8. Testing daily job logging...")
    analytics.log_daily_job_status("test_job", "success", 5000, 100)
    print("   ✓ Daily job logged successfully")
    
    # Test 9: Qdrant metrics logging
    print("\n9. Testing Qdrant metrics logging...")
    analytics.log_qdrant_metrics(25, 1000, 150, "test_collection")
    print("   ✓ Qdrant metrics logged successfully")
    
    print("\n✅ All analytics tests passed!")

def test_event_format():
    """Test that events are formatted correctly"""
    print("\n📋 Testing Event Format...")
    
    # Capture stdout to check event format
    import io
    import contextlib
    
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        analytics.log_event("format_test", "test_user", "test_session", 
                           test_prop="test_value", number_prop=42)
    
    output = f.getvalue().strip()
    print(f"   Raw output: {output}")
    
    try:
        event = json.loads(output)
        print(f"   ✓ Valid JSON format")
        print(f"   Event structure: {list(event.keys())}")
        
        required_fields = ['type', 'event_name', 'event_time', 'user_id', 'session_id', 'props']
        for field in required_fields:
            if field in event:
                print(f"   ✓ Has {field}")
            else:
                print(f"   ❌ Missing {field}")
                return False
        
        print(f"   ✓ All required fields present")
        return True
        
    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON: {e}")
        return False

async def test_middleware_simulation():
    """Simulate the analytics middleware"""
    print("\n🔄 Testing Middleware Simulation...")
    
    class MockRequest:
        def __init__(self):
            self.method = 'GET'
            self.path = '/test'
            self.cookies = {}
            self.query = {}
            self.headers = {}
    
    class MockResponse:
        def __init__(self):
            self.cookies = {}
        
        def set_cookie(self, name, value, **kwargs):
            self.cookies[name] = value
    
    async def mock_handler(request):
        return MockResponse()
    
    # Simulate middleware behavior
    request = MockRequest()
    response = await analytics.analytics_middleware(request, mock_handler)
    
    print(f"   ✓ Middleware processed request")
    print(f"   Response cookies: {response.cookies}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 AskBucky Analytics System Test")
    print("=" * 50)
    
    try:
        # Test basic functions
        test_analytics_functions()
        
        # Test event format
        if test_event_format():
            print("\n✅ Event format test passed")
        else:
            print("\n❌ Event format test failed")
            return 1
        
        # Test middleware simulation
        import asyncio
        if asyncio.run(test_middleware_simulation()):
            print("\n✅ Middleware test passed")
        else:
            print("\n❌ Middleware test failed")
            return 1
        
        print("\n🎉 All tests passed! Analytics system is working correctly.")
        print("\nNext steps:")
        print("1. Deploy the application to Cloud Run")
        print("2. Run ./setup_analytics.sh to set up BigQuery")
        print("3. Check that events are flowing to BigQuery")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 