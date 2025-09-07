#!/usr/bin/env python3
"""
Test Looker Studio Views

This script tests the BigQuery views once data is available.
Run this after deploying your application and generating some traffic.
"""

import subprocess
import json
from datetime import datetime

def test_view_exists(view_name):
    """Test if a BigQuery view exists"""
    print(f"🔍 Testing view: {view_name}")
    
    try:
        result = subprocess.run([
            'bq', 'show', f'askbucky-469317:askbucky_analytics.{view_name}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ View {view_name} exists")
            return True
        else:
            print(f"❌ View {view_name} not found: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing view {view_name}: {e}")
        return False

def test_view_data(view_name, limit=5):
    """Test if a view has data"""
    print(f"📊 Testing data in view: {view_name}")
    
    try:
        query = f'SELECT * FROM `askbucky-469317.askbucky_analytics.{view_name}` LIMIT {limit}'
        
        result = subprocess.run([
            'bq', 'query', '--use_legacy_sql=false', '--format=json', query
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                print(f"✅ View {view_name} has {len(data)} rows")
                return True
            else:
                print(f"⚠️  View {view_name} exists but has no data")
                return False
        else:
            print(f"❌ Error querying view {view_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing data in {view_name}: {e}")
        return False

def test_main_views():
    """Test the main views for Looker Studio"""
    print("🚀 Testing Looker Studio Views")
    print("=" * 50)
    
    views_to_test = [
        'events_flat',
        'v_latency_daily',
        'v_nsm_daily',
        'v_dau',
        'v_lifetime_users',
        'v_conversion_daily'
    ]
    
    results = {}
    
    for view in views_to_test:
        exists = test_view_exists(view)
        if exists:
            has_data = test_view_data(view)
            results[view] = has_data
        else:
            results[view] = False
        print()
    
    # Summary
    print("=" * 50)
    print("📋 VIEW TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for view, result in results.items():
        status = "✅ READY" if result else "❌ NOT READY"
        print(f"{view}: {status}")
    
    print(f"\nOverall: {passed}/{total} views ready for Looker Studio")
    
    if passed >= 3:
        print("\n🎉 Your views are ready for Looker Studio!")
        print("\nNext steps:")
        print("1. Go to https://lookerstudio.google.com/")
        print("2. Create a new data source")
        print("3. Connect to BigQuery")
        print("4. Select dataset: askbucky_analytics")
        print("5. Choose view: events_flat")
        print("6. Start building your dashboard!")
    else:
        print("\n⚠️  Some views are not ready yet.")
        print("\nTroubleshooting:")
        print("1. Ensure your application is deployed")
        print("2. Generate some user traffic")
        print("3. Wait 5-10 minutes for data to appear")
        print("4. Run: python verify_bigquery_setup.py")
        print("5. Then run: bq query --use_legacy_sql=false < setup_looker_views_ready.sql")
    
    return passed >= 3

def test_sample_queries():
    """Test sample queries that will be used in Looker Studio"""
    print("\n🔍 Testing Sample Looker Studio Queries")
    print("=" * 50)
    
    queries = {
        "Lifetime Unique Users": '''
        SELECT COUNT(DISTINCT user_id) AS lifetime_unique_users
        FROM `askbucky-469317.askbucky_analytics.events_flat`
        WHERE event_name IN ('page_view','ask_answered')
          AND user_id IS NOT NULL
        ''',
        
        "Today's DAU": '''
        SELECT COUNT(DISTINCT user_id) AS dau
        FROM `askbucky-469317.askbucky_analytics.events_flat`
        WHERE event_name IN ('page_view', 'ask_answered')
          AND event_date = CURRENT_DATE()
        ''',
        
        "Recent Performance": '''
        SELECT 
          event_date,
          AVG(latency_ms) AS avg_latency_ms,
          COUNT(*) AS total_requests
        FROM `askbucky-469317.askbucky_analytics.events_flat`
        WHERE event_name = 'ask_answered'
          AND event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        GROUP BY event_date
        ORDER BY event_date DESC
        LIMIT 7
        '''
    }
    
    for query_name, query in queries.items():
        print(f"\n📊 Testing: {query_name}")
        try:
            result = subprocess.run([
                'bq', 'query', '--use_legacy_sql=false', '--format=json', query
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    print(f"✅ Query successful: {len(data)} rows returned")
                    # Show first row as sample
                    if len(data) > 0:
                        print(f"   Sample: {data[0]}")
                else:
                    print("⚠️  Query successful but no data returned")
            else:
                print(f"❌ Query failed: {result.stderr}")
        except Exception as e:
            print(f"❌ Error running query: {e}")

if __name__ == "__main__":
    import sys
    
    # Test main views
    views_ready = test_main_views()
    
    # Test sample queries if views are ready
    if views_ready:
        test_sample_queries()
    
    sys.exit(0 if views_ready else 1) 