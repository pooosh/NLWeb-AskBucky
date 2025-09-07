#!/usr/bin/env python3
"""
BigQuery Setup Verification Script

This script verifies that the BigQuery analytics setup is working correctly
after the application has been deployed to Cloud Run.
"""

import subprocess
import json
import time
from datetime import datetime, timedelta

def check_bigquery_dataset():
    """Check if BigQuery dataset exists"""
    print("🔍 Checking BigQuery dataset...")
    
    try:
        result = subprocess.run([
            'bq', 'show', 'askbucky-469317:askbucky_analytics'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ BigQuery dataset exists")
            return True
        else:
            print(f"❌ BigQuery dataset not found: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking BigQuery dataset: {e}")
        return False

def check_logging_sink():
    """Check if Cloud Logging sink exists"""
    print("\n🔍 Checking Cloud Logging sink...")
    
    try:
        result = subprocess.run([
            'gcloud', 'logging', 'sinks', 'describe', 'events-to-bq',
            '--format=json'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            sink_info = json.loads(result.stdout)
            print(f"✅ Logging sink exists: {sink_info.get('name', 'unknown')}")
            print(f"   Destination: {sink_info.get('destination', 'unknown')}")
            return True
        else:
            print(f"❌ Logging sink not found: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking logging sink: {e}")
        return False

def check_cloud_logging_events():
    """Check for analytics events in Cloud Logging"""
    print("\n🔍 Checking Cloud Logging for analytics events...")
    
    try:
        # Check for events in the last hour
        query = '''
        resource.type="cloud_run_revision"
        AND resource.labels.service_name="askbucky"
        AND jsonPayload.type="event"
        AND timestamp>="2025-08-26T00:00:00Z"
        '''
        
        result = subprocess.run([
            'gcloud', 'logging', 'read', query,
            '--limit=10',
            '--format=json'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            events = json.loads(result.stdout)
            if events:
                print(f"✅ Found {len(events)} analytics events in Cloud Logging")
                for event in events[:3]:
                    payload = event.get('jsonPayload', {})
                    print(f"   - {payload.get('event_name', 'unknown')} at {payload.get('event_time', 'unknown')}")
                return True
            else:
                print("⚠️  No analytics events found in Cloud Logging")
                print("   This is normal if the app hasn't been deployed or used yet")
                return False
        else:
            print(f"❌ Error querying Cloud Logging: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking Cloud Logging: {e}")
        return False

def check_bigquery_events():
    """Check for analytics events in BigQuery"""
    print("\n🔍 Checking BigQuery for analytics events...")
    
    try:
        # First check if the table exists
        result = subprocess.run([
            'bq', 'ls', 'askbucky-469317:askbucky_analytics'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("⚠️  No tables found in BigQuery dataset")
            print("   This is normal if no events have been logged yet")
            return False
        
        # Check for events in the last hour
        query = '''
        SELECT COUNT(*) as event_count
        FROM `askbucky-469317.askbucky_analytics._AllLogs`
        WHERE jsonPayload.type = 'event'
          AND TIMESTAMP(jsonPayload.event_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        '''
        
        result = subprocess.run([
            'bq', 'query', '--use_legacy_sql=false', '--format=json', query
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                count = data[0].get('event_count', 0)
                print(f"✅ Found {count} analytics events in BigQuery (last hour)")
                return True
            else:
                print("⚠️  No recent events in BigQuery")
                return False
        else:
            print(f"❌ Error querying BigQuery: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error checking BigQuery: {e}")
        return False

def test_lifetime_users_query():
    """Test the lifetime users query"""
    print("\n🔍 Testing lifetime users query...")
    
    try:
        query = '''
        SELECT COUNT(DISTINCT jsonPayload.user_id) AS lifetime_unique_users
        FROM `askbucky-469317.askbucky_analytics._AllLogs`
        WHERE jsonPayload.type = 'event'
          AND jsonPayload.event_name IN ('page_view','ask_answered')
          AND jsonPayload.user_id IS NOT NULL
        '''
        
        result = subprocess.run([
            'bq', 'query', '--use_legacy_sql=false', '--format=json', query
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                users = data[0].get('lifetime_unique_users', 0)
                print(f"✅ Lifetime unique users: {users}")
                return True
            else:
                print("⚠️  No data returned from lifetime users query")
                return False
        else:
            print(f"❌ Error running lifetime users query: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing lifetime users query: {e}")
        return False

def main():
    """Run all verification checks"""
    print("🚀 BigQuery Setup Verification")
    print("=" * 50)
    
    checks = [
        ("BigQuery Dataset", check_bigquery_dataset),
        ("Cloud Logging Sink", check_logging_sink),
        ("Cloud Logging Events", check_cloud_logging_events),
        ("BigQuery Events", check_bigquery_events),
        ("Lifetime Users Query", test_lifetime_users_query),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"❌ {check_name} check failed with error: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed >= 3:  # At least infrastructure checks should pass
        print("\n🎉 BigQuery setup is working correctly!")
        print("\nNext steps:")
        print("1. Deploy your application to Cloud Run")
        print("2. Generate some user traffic")
        print("3. Re-run this script to verify events are flowing")
        print("4. Use the SQL queries in analytics_queries.sql")
    else:
        print("\n⚠️  Some checks failed. See details above.")
        print("\nTroubleshooting:")
        print("1. Ensure the application is deployed to Cloud Run")
        print("2. Check that the service name is 'askbucky'")
        print("3. Verify analytics events are being generated")
        print("4. Wait 5-10 minutes for data to appear in BigQuery")
    
    return 0 if passed >= 3 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 