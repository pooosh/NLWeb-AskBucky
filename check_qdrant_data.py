#!/usr/bin/env python3
"""
Check what data is in Qdrant Cloud
"""

import os
import asyncio
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient

async def check_qdrant_data():
    """Check what collections and data are in Qdrant Cloud"""
    
    # Load environment variables
    load_dotenv()
    
    qdrant_url = os.environ.get("QDRANT_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    
    if not qdrant_url:
        print("❌ QDRANT_URL not found in environment")
        return
    
    print(f"🔗 Connecting to Qdrant Cloud at: {qdrant_url}")
    
    try:
        client = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30.0)
        
        # Get all collections
        collections = await client.get_collections()
        print(f"\n📚 Found {len(collections.collections)} collections:")
        
        for collection in collections.collections:
            print(f"   - {collection.name}")
            
            # Get collection info
            info = await client.get_collection(collection.name)
            print(f"     Points: {info.points_count}")
            
            # Get a sample of points to see what sites are available
            if info.points_count > 0:
                try:
                    # Get first few points to see the data structure
                    points = await client.scroll(
                        collection_name=collection.name,
                        limit=5,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    print(f"     Sample sites found:")
                    sites = set()
                    for point in points[0]:
                        if point.payload and 'site' in point.payload:
                            sites.add(point.payload['site'])
                    
                    for site in sorted(sites):
                        print(f"       - {site}")
                        
                except Exception as e:
                    print(f"     Error getting sample data: {e}")
            
            print()
        
    except Exception as e:
        print(f"❌ Error connecting to Qdrant Cloud: {e}")

if __name__ == "__main__":
    asyncio.run(check_qdrant_data()) 