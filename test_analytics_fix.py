#!/usr/bin/env python3
"""
Test script to verify analytics fixes work locally
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code', 'python'))

from aiohttp import web
import asyncio
import analytics

async def test_analytics_functions():
    """Test analytics functions with proper response types"""
    print("🧪 Testing Analytics Functions Locally")
    print("=" * 50)
    
    # Create mock request and response
    from aiohttp.test_utils import make_mocked_request
    request = make_mocked_request('GET', '/test', headers={'User-Agent': 'test-agent'})
    
    # Test 1: Test with StreamResponse (should work)
    print("Test 1: StreamResponse (should work)")
    try:
        response = web.StreamResponse()
        uid, sid = analytics.get_or_set_ids(request, response)
        print(f"✅ StreamResponse test passed: uid={uid[:10]}..., sid={sid[:10]}...")
    except Exception as e:
        print(f"❌ StreamResponse test failed: {e}")
    
    # Test 2: Test with regular Response (should fail gracefully)
    print("\nTest 2: Regular Response (should fail gracefully)")
    try:
        response = web.Response()
        # This should not crash the server
        analytics.log_page_view(request, response, path="/test")
        print("✅ Regular Response test passed (graceful handling)")
    except Exception as e:
        print(f"❌ Regular Response test failed: {e}")
    
    # Test 3: Test analytics middleware
    print("\nTest 3: Analytics Middleware")
    try:
        async def mock_handler(req):
            return web.Response(text="OK")
        
        # Test middleware with different request types
        test_request = make_mocked_request('GET', '/static/test.html', headers={'Accept': 'text/html'})
        
        response = await analytics.analytics_middleware(test_request, mock_handler)
        print(f"✅ Middleware test passed: {response.status}")
    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary: Analytics functions should work without crashing the server")

if __name__ == "__main__":
    asyncio.run(test_analytics_functions())