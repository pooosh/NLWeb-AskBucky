#!/usr/bin/env python3
"""
Migration script to move data from local Qdrant to Qdrant Cloud.
"""

import asyncio
import os
import sys
import json
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

# Add the code/python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code', 'python'))

async def migrate_collection(
    source_client: AsyncQdrantClient,
    target_client: AsyncQdrantClient,
    collection_name: str,
    batch_size: int = 100
):
    """Migrate a collection from source to target Qdrant instance."""
    
    print(f"🔄 Migrating collection: {collection_name}")
    
    try:
        # Get collection info from source
        source_info = await source_client.get_collection(collection_name)
        print(f"   📊 Source collection info: {source_info.config.params.vectors.size} dimensions")
        
        # Create collection in target if it doesn't exist
        target_collections = await target_client.get_collections()
        target_collection_names = [c.name for c in target_collections.collections]
        
        if collection_name not in target_collection_names:
            print(f"   📝 Creating collection in target: {collection_name}")
            await target_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=source_info.config.params.vectors.size,
                    distance=source_info.config.params.vectors.distance
                )
            )
        else:
            print(f"   ✅ Collection already exists in target: {collection_name}")
        
        # Get total count
        source_count = await source_client.count(collection_name)
        print(f"   📈 Total points to migrate: {source_count.count}")
        
        if source_count.count == 0:
            print(f"   ⚠️  Collection {collection_name} is empty, skipping")
            return
        
        # Migrate points in batches
        migrated_count = 0
        offset = 0
        
        while True:
            # Get batch from source
            batch = await source_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )
            
            points = batch[0]
            if not points:
                break
            
            # Prepare points for target (ensure IDs are strings)
            target_points = []
            for point in points:
                target_points.append(models.PointStruct(
                    id=str(point.id),
                    vector=point.vector,
                    payload=point.payload
                ))
            
            # Insert batch into target
            await target_client.upsert(
                collection_name=collection_name,
                points=target_points
            )
            
            migrated_count += len(points)
            offset += len(points)
            
            print(f"   📤 Migrated {migrated_count}/{source_count.count} points ({migrated_count/source_count.count*100:.1f}%)")
            
            if len(points) < batch_size:
                break
        
        # Verify migration
        target_count = await target_client.count(collection_name)
        print(f"   ✅ Migration complete! Target has {target_count.count} points")
        
        if target_count.count == source_count.count:
            print(f"   🎉 Migration verified successfully!")
        else:
            print(f"   ⚠️  Warning: Count mismatch! Source: {source_count.count}, Target: {target_count.count}")
        
    except Exception as e:
        print(f"   ❌ Error migrating collection {collection_name}: {e}")
        raise

async def migrate_to_qdrant_cloud():
    """Main migration function."""
    
    # Configuration
    local_path = "../code/data/db"  # Local Qdrant path
    cloud_url = os.environ.get('QDRANT_URL')
    cloud_api_key = os.environ.get('QDRANT_API_KEY')
    
    if not cloud_url:
        print("❌ QDRANT_URL environment variable not set")
        return False
        
    if not cloud_api_key:
        print("❌ QDRANT_API_KEY environment variable not set")
        return False
    
    print("🚀 Starting migration from local Qdrant to Qdrant Cloud")
    print(f"   📁 Local path: {local_path}")
    print(f"   ☁️  Cloud URL: {cloud_url}")
    
    try:
        # Create clients
        local_client = AsyncQdrantClient(path=local_path)
        cloud_client = AsyncQdrantClient(url=cloud_url, api_key=cloud_api_key)
        
        # Test connections
        print("🔗 Testing connections...")
        
        local_collections = await local_client.get_collections()
        print(f"   ✅ Local Qdrant: {len(local_collections.collections)} collections")
        
        cloud_collections = await cloud_client.get_collections()
        print(f"   ✅ Qdrant Cloud: {len(cloud_collections.collections)} collections")
        
        # Get collection names to migrate
        local_collection_names = [c.name for c in local_collections.collections]
        
        if not local_collection_names:
            print("⚠️  No collections found in local Qdrant")
            return True
        
        print(f"📚 Collections to migrate: {', '.join(local_collection_names)}")
        
        # Migrate each collection
        for collection_name in local_collection_names:
            await migrate_collection(local_client, cloud_client, collection_name)
            print()  # Empty line for readability
        
        print("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
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
    
    # Run the migration
    success = asyncio.run(migrate_to_qdrant_cloud())
    sys.exit(0 if success else 1) 