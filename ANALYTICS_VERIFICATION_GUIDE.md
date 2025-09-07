# Analytics Verification Guide

This guide shows you how to verify that the AskBucky analytics system is working correctly at each stage of deployment.

## 🚀 Quick Verification Steps

### 1. **Local Testing (Always Works)**
```bash
# Test the analytics system locally
python test_analytics.py

# Run comprehensive verification
python verify_analytics.py
```

**Expected Output:**
```
✅ Local analytics system is working correctly
✅ Event format test passed
✅ Middleware test passed
```

### 2. **Check Application Logs**
```bash
# Look for analytics events in recent logs
grep -r '"type": "event"' logs/ | tail -10

# Or check specific log files
tail -50 logs/daily_load_test.log | grep "event"
```

**What to Look For:**
- JSON events with `"type": "event"`
- Events like `page_view`, `ask_answered`, `ask_started`
- Proper user_id and session_id values

### 3. **Cloud Logging Verification**
```bash
# Check for analytics events in Cloud Logging
gcloud logging read '
  resource.type="cloud_run_revision"
  AND resource.labels.service_name="askbucky"
  AND jsonPayload.type="event"
  AND timestamp>="2025-08-26T00:00:00Z"
' --limit=10 --format=json
```

**Expected Output:**
```json
[
  {
    "jsonPayload": {
      "type": "event",
      "event_name": "page_view",
      "user_id": "ab_1234567890abcdef",
      "session_id": "sess_1234567890",
      "props": { ... }
    }
  }
]
```

### 4. **BigQuery Verification**
```bash
# First, set up BigQuery infrastructure
./setup_analytics.sh

# Check if events are flowing to BigQuery
bq query --use_legacy_sql=false '
SELECT COUNT(*) as event_count
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = "event"
  AND TIMESTAMP(jsonPayload.event_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
'
```

**Expected Output:**
```
+-------------+
| event_count |
+-------------+
| 42          |
+-------------+
```

## 🔍 Detailed Verification Methods

### **Method 1: Local Development Verification**

1. **Test Analytics Module:**
   ```bash
   python test_analytics.py
   ```

2. **Check Event Format:**
   ```bash
   # Look for properly formatted JSON events
   python -c "
   import analytics
   analytics.log_event('test', 'user123', 'session456', test_prop='value')
   "
   ```

3. **Verify Cookie Handling:**
   ```bash
   # Test user ID and session ID generation
   python -c "
   import analytics
   from aiohttp import web
   
   class MockRequest:
       def __init__(self):
           self.cookies = {}
           self.query = {}
           self.headers = {}
   
   class MockResponse:
       def __init__(self):
           self.cookies = {}
       def set_cookie(self, name, value, **kwargs):
           self.cookies[name] = value
   
   request = MockRequest()
   response = MockResponse()
   uid, sid = analytics.get_or_set_ids(request, response)
   print(f'User ID: {uid}')
   print(f'Session ID: {sid}')
   print(f'Cookies: {response.cookies}')
   "
   ```

### **Method 2: Application Log Verification**

1. **Check for Analytics Events:**
   ```bash
   # Search for analytics events in all log files
   find . -name "*.log" -exec grep -l '"type": "event"' {} \;
   
   # Count analytics events in recent logs
   grep -c '"type": "event"' logs/*.log
   ```

2. **Monitor Real-time Logs:**
   ```bash
   # Watch for new analytics events
   tail -f logs/app.log | grep '"type": "event"'
   ```

3. **Verify Event Structure:**
   ```bash
   # Extract and validate event JSON
   grep '"type": "event"' logs/app.log | jq '.jsonPayload' | head -5
   ```

### **Method 3: Cloud Logging Verification**

1. **Check Recent Events:**
   ```bash
   gcloud logging read '
     resource.type="cloud_run_revision"
     AND resource.labels.service_name="askbucky"
     AND jsonPayload.type="event"
   ' --limit=5 --format=table(timestamp,jsonPayload.event_name,jsonPayload.user_id)
   ```

2. **Monitor Live Events:**
   ```bash
   # Watch for new analytics events in real-time
   gcloud logging tail '
     resource.type="cloud_run_revision"
     AND resource.labels.service_name="askbucky"
     AND jsonPayload.type="event"
   ' --format=json
   ```

3. **Check Event Types:**
   ```bash
   gcloud logging read '
     resource.type="cloud_run_revision"
     AND resource.labels.service_name="askbucky"
     AND jsonPayload.type="event"
   ' --format="value(jsonPayload.event_name)" | sort | uniq -c
   ```

### **Method 4: BigQuery Verification**

1. **Check Dataset Exists:**
   ```bash
   bq show askbucky-469317:askbucky_analytics
   ```

2. **Verify Events Table:**
   ```bash
   bq query --use_legacy_sql=false '
   SELECT COUNT(*) as total_events
   FROM `askbucky-469317.askbucky_analytics._AllLogs`
   WHERE jsonPayload.type = "event"
   '
   ```

3. **Check Recent Activity:**
   ```bash
   bq query --use_legacy_sql=false '
   SELECT 
     jsonPayload.event_name,
     COUNT(*) as event_count,
     COUNT(DISTINCT jsonPayload.user_id) as unique_users
   FROM `askbucky-469317.askbucky_analytics._AllLogs`
   WHERE jsonPayload.type = "event"
     AND TIMESTAMP(jsonPayload.event_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
   GROUP BY jsonPayload.event_name
   ORDER BY event_count DESC
   '
   ```

4. **Test Lifetime Users Query:**
   ```bash
   bq query --use_legacy_sql=false '
   SELECT COUNT(DISTINCT jsonPayload.user_id) AS lifetime_unique_users
   FROM `askbucky-469317.askbucky_analytics._AllLogs`
   WHERE jsonPayload.type = "event"
     AND jsonPayload.event_name IN ("page_view","ask_answered")
     AND jsonPayload.user_id IS NOT NULL
   '
   ```

## 🧪 Generating Test Data

### **Generate Test Events:**
```bash
# Run the verification script with test event generation
python verify_analytics.py --generate-events
```

### **Manual Test Event Generation:**
```python
import analytics

# Generate test events
analytics.log_event("page_view", "test_user", "test_session", 
                   path="/test", sitetag="test_site")

analytics.log_event("ask_started", "test_user", "test_session",
                   query="test query", site="test_site")

analytics.log_event("ask_answered", "test_user", "test_session",
                   query="test query", status="success", 
                   sources_count=3, latency_ms=1500)
```

### **Simulate User Traffic:**
```bash
# Make requests to your application
curl "https://your-app-url.com/ask?query=test&site=test_site"
curl "https://your-app-url.com/sites"
curl "https://your-app-url.com/"
```

## 📊 Verification Checklist

### **Pre-Deployment:**
- [ ] Local analytics tests pass
- [ ] Event format is correct
- [ ] Cookie handling works
- [ ] UTM parameter extraction works

### **Post-Deployment:**
- [ ] Application is deployed to Cloud Run
- [ ] BigQuery infrastructure is set up
- [ ] Events appear in Cloud Logging
- [ ] Events flow to BigQuery
- [ ] Analytics queries return data

### **Ongoing Monitoring:**
- [ ] Daily active users are tracked
- [ ] Lifetime unique users are counted
- [ ] Conversion rates are calculated
- [ ] Error rates are monitored
- [ ] Performance metrics are logged

## 🚨 Troubleshooting

### **No Events in Cloud Logging:**
1. Check if application is deployed
2. Verify service name in log filter
3. Check application logs for errors
4. Ensure analytics middleware is loaded

### **No Events in BigQuery:**
1. Run `./setup_analytics.sh`
2. Check log sink configuration
3. Verify IAM permissions
4. Check for data latency (can take 5-10 minutes)

### **Events Not Being Generated:**
1. Check if analytics module is imported
2. Verify middleware is configured
3. Check for JavaScript errors in browser
4. Ensure cookies are enabled

### **Invalid Event Format:**
1. Check JSON structure
2. Verify required fields are present
3. Check for encoding issues
4. Validate event schema

## 📈 Performance Monitoring

### **Check Analytics Overhead:**
```bash
# Monitor response times with and without analytics
curl -w "@curl-format.txt" -o /dev/null -s "https://your-app-url.com/ask?query=test"
```

### **Monitor BigQuery Costs:**
```bash
# Check query costs
bq query --use_legacy_sql=false --dry_run '
SELECT COUNT(*) FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = "event"
'
```

### **Check Log Volume:**
```bash
# Monitor log ingestion rate
gcloud logging read '
  resource.type="cloud_run_revision"
  AND resource.labels.service_name="askbucky"
  AND jsonPayload.type="event"
' --format="value(timestamp)" | wc -l
```

## 🎯 Success Indicators

### **Working Analytics System:**
- ✅ Events appear in Cloud Logging within 1 minute
- ✅ Events appear in BigQuery within 10 minutes
- ✅ User IDs are consistent across sessions
- ✅ Session IDs change every 30 minutes
- ✅ UTM parameters are captured correctly
- ✅ Error events are logged for debugging
- ✅ Performance metrics are within acceptable ranges

### **Key Metrics to Monitor:**
- **Event Volume**: Should match your traffic
- **User Growth**: Should show new users daily
- **Error Rate**: Should be < 5%
- **Latency**: Analytics should add < 100ms
- **Data Freshness**: Events should appear within 10 minutes

This verification guide ensures your analytics system is working correctly at every stage of deployment and operation. 