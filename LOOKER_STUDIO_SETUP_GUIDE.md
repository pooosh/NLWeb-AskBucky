# Looker Studio Dashboard Setup Guide

This guide walks you through setting up a comprehensive analytics dashboard in Looker Studio using your BigQuery analytics data.

## 🚀 **Prerequisites**

1. **BigQuery Setup Complete** ✅
   - Dataset: `askbucky-469317:askbucky_analytics`
   - Log sink: `events-to-bq`
   - IAM permissions configured

2. **Application Deployed** 
   - Deploy your AskBucky application to Cloud Run
   - Generate some user traffic
   - Verify events are flowing to BigQuery

3. **Data Available**
   - Run `python verify_bigquery_setup.py` to confirm data is flowing
   - Wait 5-10 minutes for data to appear in BigQuery

## 📊 **Step 1: Create BigQuery Views**

Once your application is deployed and events are flowing, create the views:

```bash
# Execute the views setup
bq query --use_legacy_sql=false < setup_looker_views_ready.sql
```

Or run individual views:

```bash
# Main flat view
bq query --use_legacy_sql=false '
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.events_flat` AS
SELECT
  TIMESTAMP(jsonPayload.event_time) AS event_ts,
  DATE(TIMESTAMP(jsonPayload.event_time)) AS event_date,
  jsonPayload.event_name AS event_name,
  jsonPayload.user_id AS user_id,
  jsonPayload.session_id AS session_id,
  SAFE_CAST(jsonPayload.props.latency_ms AS INT64) AS latency_ms,
  SAFE_CAST(jsonPayload.props.sources_count AS INT64) AS sources_count,
  jsonPayload.props.status AS status,
  jsonPayload.props.site AS site,
  jsonPayload.props.utm_source AS utm_source
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = "event"
'
```

## 🎯 **Step 2: Set Up Looker Studio**

### **2.1 Create Data Source**

1. Go to [Looker Studio](https://lookerstudio.google.com/)
2. Click **"Create"** → **"Data Source"**
3. Select **"BigQuery"** connector
4. Choose your project: `askbucky-469317`
5. Select dataset: `askbucky_analytics`
6. Choose view: `events_flat`
7. Click **"Connect"**

### **2.2 Configure Data Source**

In the data source configuration:

1. **Set Date Range**: 
   - Default: Last 30 days
   - Add date range controls for dashboard

2. **Add Parameters**:
   - `event_date` (Date)
   - `event_name` (Text)
   - `site` (Text)
   - `status` (Text)

3. **Click "Create Report"**

## 📈 **Step 3: Build Dashboard**

### **3.1 Key Metrics Cards**

Create scorecards for important metrics:

**North Star Metric (Daily Satisfied Answers)**
- Data Source: `v_nsm_daily`
- Metric: `nsm_count`
- Comparison: Previous period

**Daily Active Users**
- Data Source: `v_dau`
- Metric: `dau`
- Comparison: Previous period

**Lifetime Unique Users**
- Data Source: `v_lifetime_users`
- Metric: `lifetime_unique_users`
- Show latest value

**Conversion Rate**
- Data Source: `v_conversion_daily`
- Metric: `conversion_rate_percent`
- Format: Percentage

### **3.2 Time Series Charts**

**User Growth Over Time**
- Chart Type: Line Chart
- Data Source: `v_dau`
- X-Axis: `event_date`
- Y-Axis: `dau`
- Add trend line

**North Star Metric Trend**
- Chart Type: Line Chart
- Data Source: `v_nsm_daily`
- X-Axis: `event_date`
- Y-Axis: `nsm_count`
- Add target line at 100

**Performance Metrics**
- Chart Type: Line Chart
- Data Source: `v_latency_daily`
- X-Axis: `event_date`
- Y-Axis: `p50_ms`, `p75_ms`, `p90_ms`
- Multiple lines for different percentiles

### **3.3 Bar Charts**

**Site Performance**
- Chart Type: Bar Chart
- Data Source: `v_site_performance`
- X-Axis: `site`
- Y-Axis: `success_rate_percent`
- Sort by success rate

**Traffic Sources**
- Chart Type: Bar Chart
- Data Source: `v_traffic_sources`
- X-Axis: `utm_source`
- Y-Axis: `unique_users`
- Filter by recent date range

**Error Analysis**
- Chart Type: Bar Chart
- Data Source: `v_errors_daily`
- X-Axis: `error_type`
- Y-Axis: `error_count`
- Sort by error count

### **3.4 Tables**

**Recent Activity**
- Chart Type: Table
- Data Source: `events_flat`
- Columns: `event_date`, `event_name`, `user_id`, `site`, `status`
- Sort by `event_date` DESC
- Limit to 100 rows

**Top Performing Sites**
- Chart Type: Table
- Data Source: `v_site_performance`
- Columns: `site`, `total_asks`, `success_rate_percent`, `avg_latency_ms`
- Sort by `total_asks` DESC

## 🎨 **Step 4: Dashboard Design**

### **4.1 Layout Structure**

```
┌─────────────────────────────────────────────────────────┐
│                    AskBucky Analytics                    │
├─────────────────────────────────────────────────────────┤
│  [NSM] [DAU] [Lifetime Users] [Conversion Rate]        │
├─────────────────────────────────────────────────────────┤
│  User Growth Chart    │  Performance Metrics           │
│                       │                                │
├─────────────────────────────────────────────────────────┤
│  Site Performance     │  Traffic Sources               │
│                       │                                │
├─────────────────────────────────────────────────────────┤
│                    Recent Activity Table                │
└─────────────────────────────────────────────────────────┘
```

### **4.2 Styling**

1. **Color Scheme**:
   - Primary: Blue (#4285F4)
   - Success: Green (#34A853)
   - Warning: Orange (#FBBC04)
   - Error: Red (#EA4335)

2. **Typography**:
   - Headers: Roboto, 18-24px
   - Body: Roboto, 12-14px
   - Metrics: Roboto, 24-36px

3. **Spacing**:
   - Consistent 16px margins
   - 8px padding between elements

## 🔧 **Step 5: Advanced Features**

### **5.1 Filters**

Add dashboard-level filters:

1. **Date Range Filter**:
   - Type: Date Range
   - Default: Last 30 days
   - Apply to all charts

2. **Site Filter**:
   - Type: Dropdown
   - Source: `events_flat.site`
   - Apply to relevant charts

3. **Event Type Filter**:
   - Type: Dropdown
   - Source: `events_flat.event_name`
   - Apply to activity tables

### **5.2 Calculated Fields**

Create custom metrics:

**Success Rate**
```
CASE 
  WHEN event_name = 'ask_answered' THEN
    IF(status = 'success', 1, 0)
  ELSE NULL
END
```

**Response Time Category**
```
CASE 
  WHEN latency_ms <= 1000 THEN 'Fast (<1s)'
  WHEN latency_ms <= 3000 THEN 'Good (1-3s)'
  WHEN latency_ms <= 5000 THEN 'Slow (3-5s)'
  ELSE 'Very Slow (>5s)'
END
```

### **5.3 Conditional Formatting**

Apply color coding:

**Success Rate Colors**:
- > 90%: Green
- 70-90%: Yellow
- < 70%: Red

**Latency Colors**:
- < 1000ms: Green
- 1000-3000ms: Yellow
- > 3000ms: Red

## 📱 **Step 6: Mobile Optimization**

1. **Responsive Layout**:
   - Use flexible grid layouts
   - Test on mobile devices
   - Adjust font sizes for mobile

2. **Touch-Friendly**:
   - Large filter buttons
   - Easy-to-tap chart elements
   - Swipe-friendly tables

## 🔄 **Step 7: Automation**

### **7.1 Scheduled Refresh**

1. **Data Refresh**: BigQuery views update automatically
2. **Dashboard Refresh**: Set to refresh every hour
3. **Email Reports**: Schedule weekly/monthly reports

### **7.2 Alerts**

Set up alerts for:

1. **Performance Degradation**:
   - P50 latency > 3000ms
   - Success rate < 80%

2. **User Growth**:
   - DAU drop > 20%
   - No new users for 24 hours

3. **Error Spikes**:
   - Error rate > 5%
   - New error types detected

## 📊 **Recommended Dashboard Views**

### **Executive Dashboard**
- North Star Metric
- User growth trends
- High-level performance metrics
- Key business indicators

### **Operations Dashboard**
- Detailed performance metrics
- Error analysis
- Site-specific performance
- System health indicators

### **Marketing Dashboard**
- Traffic source analysis
- Conversion rates
- User acquisition metrics
- Campaign performance

## 🔗 **Quick Links**

- **Looker Studio**: https://lookerstudio.google.com/
- **BigQuery Console**: https://console.cloud.google.com/bigquery?project=askbucky-469317
- **Dataset**: `askbucky-469317.askbucky_analytics`
- **Main View**: `events_flat`

## 🎯 **Success Metrics**

Your dashboard should help you track:

1. **North Star Metric**: Daily Satisfied Answers
2. **User Growth**: DAU, MAU, Lifetime Users
3. **Performance**: Response times, success rates
4. **Quality**: Error rates, user satisfaction
5. **Growth**: Conversion rates, traffic sources

This dashboard will give you comprehensive insights into AskBucky's performance and help you make data-driven decisions to improve the product! 