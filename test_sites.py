#!/usr/bin/env python3
"""
Test what sites are available through the retriever
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_sites():
    """Test what sites are available through the retriever"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize the retriever
        from core.retriever import get_vector_db_client
        
        # Get the retriever client
        retriever = get_vector_db_client()
        
        # Get available sites
        sites = await retriever.get_sites()
        
        print(f"🔍 Available sites through retriever:")
        for site in sites:
            print(f"   - {site}")
            
        # Test a search query
        print(f"\n🔍 Testing search for 'pizza':")
        results = await retriever.search("pizza", top_k=3)
        
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"   {i+1}. Score: {result.score:.3f}, Site: {result.payload.get('site', 'N/A')}")
            print(f"      Title: {result.payload.get('title', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error testing sites: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sites()) 