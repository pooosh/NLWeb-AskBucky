#!/usr/bin/env python3
"""
Test script to verify Qdrant Cloud connection and basic operations.
"""

import asyncio
import os
import sys
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

# Add the code/python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code', 'python'))

async def test_qdrant_cloud():
    """Test Qdrant Cloud connection and basic operations."""
    
    # Get configuration from environment
    qdrant_url = os.environ.get('QDRANT_URL')
    qdrant_api_key = os.environ.get('QDRANT_API_KEY')
    
    if not qdrant_url:
        print("❌ QDRANT_URL environment variable not set")
        return False
        
    if not qdrant_api_key:
        print("❌ QDRANT_API_KEY environment variable not set")
        return False
    
    print(f"🔗 Connecting to Qdrant Cloud at: {qdrant_url}")
    
    try:
        # Create client
        client = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        
        # Test connection by getting collections
        collections = await client.get_collections()
        print(f"✅ Successfully connected to Qdrant Cloud!")
        print(f"📚 Found {len(collections.collections)} collections:")
        
        for collection in collections.collections:
            print(f"   - {collection.name}")
        
        # Test creating a test collection
        test_collection_name = "test_collection"
        
        # Check if test collection exists
        collection_names = [c.name for c in collections.collections]
        if test_collection_name in collection_names:
            print(f"🗑️  Deleting existing test collection: {test_collection_name}")
            await client.delete_collection(test_collection_name)
        
        # Create test collection
        print(f"📝 Creating test collection: {test_collection_name}")
        await client.create_collection(
            collection_name=test_collection_name,
            vectors_config=models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE
            )
        )
        
        # Test inserting a point
        test_point = models.PointStruct(
            id=1,  # Use integer ID instead of string
            vector=[0.1] * 1536,  # Simple test vector
            payload={"test": "data", "message": "Hello from AskBucky!"}
        )
        
        print("📤 Inserting test point...")
        await client.upsert(
            collection_name=test_collection_name,
            points=[test_point]
        )
        
        # Test searching
        print("🔍 Testing search...")
        search_result = await client.search(
            collection_name=test_collection_name,
            query_vector=[0.1] * 1536,
            limit=1
        )
        
        if search_result:
            print(f"✅ Search successful! Found {len(search_result)} results")
            print(f"   First result payload: {search_result[0].payload}")
        else:
            print("❌ Search returned no results")
        
        # Clean up test collection
        print(f"🧹 Cleaning up test collection: {test_collection_name}")
        await client.delete_collection(test_collection_name)
        
        print("🎉 All tests passed! Qdrant Cloud is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Qdrant Cloud: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print("📄 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value
    
    # Run the test
    success = asyncio.run(test_qdrant_cloud())
    sys.exit(0 if success else 1) 