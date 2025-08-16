#!/usr/bin/env python3
"""
Script to check what data is currently in the vector database.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retriever import get_vector_db_client


async def check_database_contents():
    """Check what data is currently in the vector database"""
    print("🔍 Checking vector database contents...")
    
    try:
        # Get the vector database client
        retriever = get_vector_db_client()
        
        # Get all sites in the database
        all_sites = await retriever.get_sites()
        
        if not all_sites:
            print("✅ Vector database is empty!")
            return
        
        print(f"📋 Found {len(all_sites)} sites in database:")
        print("=" * 50)
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_sites = []
        other_sites = []
        
        for site in all_sites:
            if today in site:
                today_sites.append(site)
            else:
                other_sites.append(site)
        
        if today_sites:
            print(f"📅 TODAY'S DATA ({len(today_sites)} sites):")
            for site in today_sites:
                print(f"  ✅ {site}")
        
        if other_sites:
            print(f"📅 OTHER DATA ({len(other_sites)} sites):")
            for site in other_sites:
                print(f"  ❌ {site}")
        
        print("=" * 50)
        
        if not other_sites:
            print("🎉 SUCCESS: Only today's data is in the database!")
        else:
            print("⚠️  WARNING: Found data from other dates in the database!")
            print(f"   Today's sites: {len(today_sites)}")
            print(f"   Other sites: {len(other_sites)}")
        
    except Exception as e:
        print(f"❌ Error checking vector database: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 Checking vector database contents...")
    success = asyncio.run(check_database_contents())
    
    if not success:
        sys.exit(1) 