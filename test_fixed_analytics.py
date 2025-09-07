#!/usr/bin/env python3
"""
Test script to verify the FIXED analytics works properly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code', 'python'))

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
import asyncio
import analytics_fixed

async def test_fixed_analytics():
    """Test the fixed analytics functions"""
    print("🧪 Testing FIXED Analytics Functions")
    print("=" * 50)
    
    # Create mock request
    request = make_mocked_request('GET', '/test', headers={'User-Agent': 'test-agent'})
    
    # Test 1: Test with StreamResponse
    print("Test 1: StreamResponse")
    try:
        response = web.StreamResponse()
        uid, sid = analytics_fixed.get_or_set_ids(request, response)
        print(f"✅ StreamResponse test passed: uid={uid[:10]}..., sid={sid[:10]}...")
    except Exception as e:
        print(f"❌ StreamResponse test failed: {e}")
    
    # Test 2: Test with regular Response
    print("\nTest 2: Regular Response")
    try:
        response = web.Response()
        analytics_fixed.log_page_view(request, response, path="/test")
        print("✅ Regular Response test passed")
    except Exception as e:
        print(f"❌ Regular Response test failed: {e}")
    
    # Test 3: Test middleware with proper handler chain
    print("\nTest 3: Fixed Analytics Middleware")
    try:
        async def mock_handler(req):
            return web.Response(text="OK")
        
        test_request = make_mocked_request('GET', '/static/test.html', headers={'Accept': 'text/html'})
        
        response = await analytics_fixed.analytics_middleware(test_request, mock_handler)
        print(f"✅ Fixed middleware test passed: {response.status}")
    except Exception as e:
        print(f"❌ Fixed middleware test failed: {e}")
    
    # Test 4: Test middleware with error handling
    print("\nTest 4: Middleware Error Handling")
    try:
        async def error_handler(req):
            raise Exception("Test error")
        
        test_request = make_mocked_request('GET', '/test', headers={'Accept': 'text/html'})
        
        try:
            response = await analytics_fixed.analytics_middleware(test_request, error_handler)
            print("❌ Should have raised an exception")
        except Exception as e:
            print(f"✅ Error handling test passed: {e}")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Fixed Analytics Test Summary: All tests should pass!")

if __name__ == "__main__":
    asyncio.run(test_fixed_analytics())