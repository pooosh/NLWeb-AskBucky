# AskBucky Analytics System

This document describes the privacy-friendly analytics system implemented for AskBucky to enable data-driven decision making.

## Overview

The analytics system provides lightweight, privacy-friendly product analytics that you fully control using your existing stack (Cloud Run + Cloud Logging + BigQuery). It tracks key metrics like DAU/MAU, conversion rates, retention, and performance metrics without compromising user privacy.

## Key Features

- **Privacy-First**: Anonymous user tracking with no PII collection
- **Lightweight**: Minimal performance impact
- **Self-Hosted**: You control all data
- **Real-Time**: Events stream directly to BigQuery
- **Comprehensive**: Tracks user behavior, performance, and operational metrics

## Metrics Tracked

### User Metrics
- **DAU/MAU**: Daily and Monthly Active Users
- **Lifetime Unique Users**: Total unique users since launch
- **Conversion Rate**: % of sessions with successful answers
- **Retention**: User return rates (1-day, 7-day, 30-day)
- **Churn**: 1 - retention rate

### Performance Metrics
- **Answer Success Rate**: % of queries returning results
- **Latency**: Response time percentiles
- **Qdrant Hit Rate**: Vector search effectiveness
- **Error Rates**: Application error tracking

### North Star Metric
- **Daily Satisfied Answers (DSA)**: Count of successful answers with sources and fast response time

### Operational Metrics
- **Daily Job Status**: Data loading and maintenance jobs
- **Site Performance**: Per-site success rates and usage
- **Traffic Sources**: UTM parameter tracking

## Architecture

```
User Request → aiohttp Server → Analytics Middleware → Cloud Logging → BigQuery
```

### Components

1. **Analytics Module** (`analytics.py`): Core tracking functionality
2. **Middleware**: Automatic page view and error tracking
3. **API Integration**: Enhanced request handlers with analytics
4. **BigQuery Sink**: Cloud Logging to BigQuery pipeline
5. **SQL Queries**: Ready-to-run analytics queries

## Setup Instructions

### 1. Deploy Updated Application

The analytics system is already integrated into your aiohttp server. Deploy the updated code to Cloud Run:

```bash
# Build and deploy to Cloud Run
gcloud run deploy askbucky \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 2. Set Up BigQuery Infrastructure

Run the setup script to create the BigQuery dataset and log sink:

```bash
cd NLWeb
./setup_analytics.sh
```

This script will:
- Create the BigQuery dataset
- Set up Cloud Logging sink to BigQuery
- Configure proper IAM permissions

### 3. Verify Data Flow

Check if events are flowing to BigQuery:

```bash
# Check recent events
bq query --use_legacy_sql=false '
SELECT COUNT(*) as event_count 
FROM `askbucky-469317.askbucky_analytics._AllLogs` 
WHERE jsonPayload.type="event" 
  AND TIMESTAMP(jsonPayload.event_time) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
'
```

## Event Schema

All events follow this JSON structure:

```json
{
  "type": "event",
  "event_name": "ask_answered",
  "event_time": "2025-08-19T12:34:56Z",
  "user_id": "ab_0c7f...e1",
  "session_id": "sess_20250819_1234",
  "props": {
    "site": "gordon-avenue-market",
    "sitetag": "menus_2025-08-19",
    "status": "success",
    "sources_count": 3,
    "latency_ms": 1420,
    "query_len": 48,
    "model": "gpt-4o-mini",
    "qdrant_hits": 41,
    "utm_source": "direct",
    "utm_medium": "(none)",
    "utm_campaign": "(none)"
  }
}
```

## Event Types

### User Events
- `page_view`: User visits a page
- `ask_started`: User submits a question
- `ask_answered`: Question is answered (success/empty/error)

### System Events
- `error`: Application errors
- `daily_job`: Background job execution
- `qdrant_metrics`: Vector search performance

## Analytics Queries

Use the queries in `analytics_queries.sql` to analyze your data:

### Key Metrics
```sql
-- DAU (Daily Active Users)
SELECT DATE(TIMESTAMP(jsonPayload.event_time)) AS date,
       COUNT(DISTINCT jsonPayload.user_id) AS dau
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = 'event'
  AND jsonPayload.event_name IN ('ask_answered', 'page_view')
GROUP BY date
ORDER BY date;

-- Lifetime Unique Users
SELECT COUNT(DISTINCT jsonPayload.user_id) AS lifetime_unique_users
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = 'event'
  AND jsonPayload.event_name IN ('page_view','ask_answered')
  AND jsonPayload.user_id IS NOT NULL;
```

### Conversion Analysis
```sql
-- Session Conversion Rate
WITH sessions AS (
  SELECT jsonPayload.session_id AS sid,
         MAX(IF(jsonPayload.event_name = 'ask_answered' 
                AND jsonPayload.props.status = 'success', 1, 0)) AS converted
  FROM `askbucky-469317.askbucky_analytics._AllLogs`
  WHERE jsonPayload.type = 'event'
  GROUP BY sid
)
SELECT SAFE_DIVIDE(SUM(converted), COUNT(*)) AS session_conversion_rate
FROM sessions;
```

### Performance Monitoring
```sql
-- Answer Success Rate + Latency
SELECT SAFE_DIVIDE(
         SUM(IF(jsonPayload.props.status = 'success', 1, 0)),
         COUNTIF(jsonPayload.event_name = 'ask_answered')
       ) AS answer_success_rate,
       APPROX_QUANTILES(CAST(jsonPayload.props.latency_ms AS INT64), 2)[OFFSET(1)] AS p50_latency_ms
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = 'event'
  AND jsonPayload.event_name = 'ask_answered';
```

## Privacy Considerations

### Data Minimization
- No PII collection (names, emails, etc.)
- Anonymous user IDs (cookies)
- Session-based tracking (30-minute windows)
- No IP address logging

### User Control
- Cookies are HTTP-only and secure
- Users can clear cookies to reset tracking
- No cross-site tracking
- Data stays within your Google Cloud project

### Compliance
- GDPR-friendly (anonymous data)
- No third-party tracking
- Full data ownership
- Easy data deletion capability

## Monitoring and Alerts

### Key Metrics to Monitor
1. **Answer Success Rate**: Should be > 80%
2. **Average Latency**: Should be < 3 seconds
3. **Error Rate**: Should be < 5%
4. **Daily Active Users**: Track growth trends

### Setting Up Alerts
Create Cloud Monitoring alerts for:
- High error rates
- Slow response times
- Failed daily jobs
- Unusual traffic patterns

## Troubleshooting

### No Events in BigQuery
1. Check Cloud Logging for events
2. Verify log sink configuration
3. Check IAM permissions
4. Ensure application is deployed

### Missing User Tracking
1. Check cookie settings
2. Verify HTTPS is enabled
3. Check browser console for errors
4. Verify analytics middleware is loaded

### Performance Issues
1. Monitor analytics overhead
2. Check BigQuery costs
3. Optimize query performance
4. Consider data retention policies

## Cost Optimization

### BigQuery Costs
- Events are stored in `_AllLogs` table
- Consider partitioning by date
- Set up data retention policies
- Monitor query costs

### Logging Costs
- Events go to Cloud Logging first
- Consider log exclusion filters
- Monitor log volume
- Set up log retention

## Future Enhancements

### Planned Features
- [ ] User feedback tracking (thumbs up/down)
- [ ] A/B testing framework
- [ ] Cohort analysis dashboard
- [ ] Revenue tracking (when applicable)
- [ ] Advanced funnel analysis

### Custom Events
You can add custom events by calling:
```python
analytics.log_event("custom_event", user_id, session_id, 
                   custom_prop1="value1", custom_prop2="value2")
```

## Lifetime Unique Users Tracking

The analytics system includes comprehensive lifetime unique users tracking with the following capabilities:

### Core Metrics
- **Total Lifetime Unique Users**: Single number showing all-time unique users
- **New Users per Day**: Daily new user acquisition
- **Cumulative Growth**: Day-by-day growth of total unique users

### Advanced Analytics
- **User Segmentation**: Power users, active users, casual users, one-time users
- **Engagement Analysis**: Events per user, active days, success rates
- **Acquisition Analysis**: User retention by traffic source
- **Cohort Analysis**: Monthly user cohorts and retention rates

### Real-Time Dashboard Queries
- **Today's Activity**: New vs returning users today
- **Weekly Growth**: Week-over-week user growth trends
- **Monthly Trends**: Monthly growth rates and patterns

Use the queries in `lifetime_users_queries.sql` for comprehensive lifetime user analytics.

## Support

For issues or questions:
1. Check the logs in Cloud Logging
2. Review BigQuery data structure
3. Test with sample queries
4. Contact the development team

## Files Modified

- `analytics.py`: Core analytics module
- `webserver/routes/api.py`: Enhanced API handlers
- `webserver/middleware/__init__.py`: Analytics middleware
- `core/baseHandler.py`: Enhanced query tracking
- `robust_load_today.py`: Job status tracking
- `setup_analytics.sh`: Infrastructure setup script
- `analytics_queries.sql`: Ready-to-run SQL queries
- `lifetime_users_queries.sql`: Dedicated lifetime unique users analytics

## Quick Start Checklist

- [ ] Deploy updated application to Cloud Run
- [ ] Run `./setup_analytics.sh`
- [ ] Verify events are flowing to BigQuery
- [ ] Test key metrics queries
- [ ] Set up monitoring alerts
- [ ] Review privacy settings
- [ ] Document custom events (if needed) 