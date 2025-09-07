#!/usr/bin/env python3
"""
Analytics Verification Script for AskBucky

This script helps verify that analytics logging is working correctly
in different environments (local, staging, production).
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime, timedelta

def check_local_analytics():
    """Check if local analytics system is working"""
    print("🔍 Checking Local Analytics System...")
    
    try:
        # Run the test script
        result = subprocess.run([sys.executable, 'test_analytics.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Local analytics system is working correctly")
            return True
        else:
            print(f"❌ Local analytics test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running local test: {e}")
        return False

def check_cloud_logging():
    """Check if events are appearing in Cloud Logging"""
    print("\n🔍 Checking Cloud Logging...")
    
    try:
        # Check for recent analytics events in Cloud Logging
        query = '''
        resource.type="cloud_run_revision"
        AND resource.labels.service_name="askbucky"
        AND jsonPayload.type="event"
        AND timestamp>="2025-08-26T00:00:00Z"
        '''
        
        # Use gcloud to query logs
        cmd = [
            'gcloud', 'logging', 'read', query,
            '--limit=10',
            '--format=json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logs = json.loads(result.stdout)
            if logs:
                print(f"✅ Found {len(logs)} analytics events in Cloud Logging")
                for log in logs[:3]:  # Show first 3 events
                    event = log.get('jsonPayload', {})
                    print(f"   - {event.get('event_name', 'unknown')} at {event.get('event_time', 'unknown')}")
                return True
            else:
                print("⚠️  No analytics events found in Cloud Logging")
                print("   This might be normal if the app hasn't been deployed yet")
                return False
        else:
            print(f"❌ Error querying Cloud Logging: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Cloud Logging: {e}")
        return False

def check_bigquery():
    """Check if events are flowing to BigQuery"""
    print("\n🔍 Checking BigQuery...")
    
    try:
        # Check if the dataset exists
        cmd = [
            'bq', 'show', 'askbucky-469317:askbucky_analytics'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ BigQuery dataset not found. Run ./setup_analytics.sh first")
            return False
        
        # Check for recent events
        query = '''
        SELECT COUNT(*) as event_count
        FROM `askbucky-469317.askbucky_analytics._AllLogs`
        WHERE jsonPayload.type = 'event'
          AND TIMESTAMP(jsonPayload.event_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        '''
        
        cmd = [
            'bq', 'query', '--use_legacy_sql=false', '--format=json', query
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
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

def check_application_logs():
    """Check application logs for analytics output"""
    print("\n🔍 Checking Application Logs...")
    
    try:
        # Look for analytics events in recent logs
        log_files = [
            'logs/daily_load_test.log',
            'logs/app.log',
            'logs/analytics.log'
        ]
        
        found_events = False
        for log_file in log_files:
            if os.path.exists(log_file):
                print(f"   Checking {log_file}...")
                
                # Look for analytics events in the last 100 lines
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                    
                    for line in recent_lines:
                        if '"type": "event"' in line or '"event_name"' in line:
                            print(f"   ✅ Found analytics event in {log_file}")
                            found_events = True
                            break
        
        if not found_events:
            print("   ⚠️  No analytics events found in log files")
            print("   This might be normal if the app hasn't been used recently")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking application logs: {e}")
        return False

def generate_test_events():
    """Generate some test events to verify logging"""
    print("\n🧪 Generating Test Events...")
    
    try:
        # Import analytics module
        sys.path.insert(0, os.path.join(os.getcwd(), 'code', 'python'))
        import analytics
        
        # Generate test events
        test_events = [
            ("page_view", {"path": "/test", "sitetag": "test"}),
            ("ask_started", {"query": "test query", "site": "test_site"}),
            ("ask_answered", {"query": "test query", "status": "success", "sources_count": 1, "latency_ms": 1000}),
            ("daily_job", {"job_name": "test_job", "status": "success", "duration_ms": 5000}),
        ]
        
        for event_name, props in test_events:
            analytics.log_event(event_name, "test_user", "test_session", **props)
            print(f"   ✅ Generated {event_name} event")
        
        print("   Test events generated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error generating test events: {e}")
        return False

def check_environment():
    """Check if required tools are available"""
    print("🔍 Checking Environment...")
    
    tools = {
        'gcloud': 'Google Cloud CLI',
        'bq': 'BigQuery CLI',
        'python': 'Python'
    }
    
    missing_tools = []
    for tool, description in tools.items():
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"   ✅ {description} ({tool}) is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"   ❌ {description} ({tool}) is not available")
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n⚠️  Missing tools: {', '.join(missing_tools)}")
        print("   Some verification steps may fail")
    
    return len(missing_tools) == 0

def main():
    """Run all verification checks"""
    print("🚀 AskBucky Analytics Verification")
    print("=" * 50)
    
    checks = [
        ("Environment", check_environment),
        ("Local Analytics", check_local_analytics),
        ("Application Logs", check_application_logs),
        ("Cloud Logging", check_cloud_logging),
        ("BigQuery", check_bigquery),
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
    
    if passed == total:
        print("\n🎉 All checks passed! Analytics system is working correctly.")
    else:
        print("\n⚠️  Some checks failed. See details above.")
        print("\nNext steps:")
        print("1. Deploy the application to Cloud Run")
        print("2. Run ./setup_analytics.sh to set up BigQuery")
        print("3. Generate some test traffic")
        print("4. Re-run this verification script")
    
    # Generate test events if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--generate-events':
        generate_test_events()
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main()) 