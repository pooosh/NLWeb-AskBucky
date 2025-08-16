#!/usr/bin/env python3
"""
Simple script to clear all data from the vector database.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retriever import get_vector_db_client


async def clear_vector_database():
    """Clear all data from the vector database"""
    print("🗑️  Clearing vector database...")
    
    try:
        # Get the vector database client
        retriever = get_vector_db_client()
        
        # Get all sites in the database
        all_sites = await retriever.get_all_sites()
        
        if not all_sites:
            print("✅ Vector database is already empty!")
            return
        
        print(f"📋 Found {len(all_sites)} sites to delete: {all_sites}")
        
        # Delete documents for each site
        total_deleted = 0
        for site in all_sites:
            deleted_count = await retriever.delete_documents_by_site(site)
            total_deleted += deleted_count
            print(f"  🗑️  Deleted {deleted_count} documents from site: {site}")
        
        print(f"✅ Successfully deleted {total_deleted} total documents from vector database!")
        
    except Exception as e:
        print(f"❌ Error clearing vector database: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 Starting vector database cleanup...")
    success = asyncio.run(clear_vector_database())
    
    if success:
        print("🎉 Vector database cleared successfully!")
    else:
        print("💥 Failed to clear vector database!")
        sys.exit(1) 