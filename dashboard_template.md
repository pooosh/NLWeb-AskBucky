# AskBucky Dashboard Template

## 🎯 **Executive Summary Dashboard**

### **Top Row - Key Metrics (Scorecards)**
```
┌─────────────────────────────────────────────────────────┐
│  [North Star Metric] [DAU] [Lifetime Users] [Conv Rate] │
│  [1,234]           [567]  [8,901]         [85.2%]      │
└─────────────────────────────────────────────────────────┘
```

**Data Sources:**
- North Star Metric: `v_nsm_daily.nsm_count` (latest)
- DAU: `v_dau.dau` (latest)
- Lifetime Users: `v_lifetime_users.lifetime_unique_users` (latest)
- Conversion Rate: `v_conversion_daily.conversion_rate_percent` (latest)

### **Second Row - Growth Charts**
```
┌─────────────────────────────────────────────────────────┐
│  User Growth Trend    │  North Star Metric Trend       │
│  [Line Chart]        │  [Line Chart]                   │
│  X: event_date       │  X: event_date                  │
│  Y: dau              │  Y: nsm_count                   │
└─────────────────────────────────────────────────────────┘
```

**Data Sources:**
- User Growth: `v_dau` (last 30 days)
- NSM Trend: `v_nsm_daily` (last 30 days)

### **Third Row - Performance & Quality**
```
┌─────────────────────────────────────────────────────────┐
│  Response Time Metrics │  Site Performance             │
│  [Line Chart]         │  [Bar Chart]                  │
│  X: event_date        │  X: site                      │
│  Y: p50_ms, p75_ms    │  Y: success_rate_percent      │
└─────────────────────────────────────────────────────────┘
```

**Data Sources:**
- Performance: `v_latency_daily` (last 30 days)
- Site Performance: `v_site_performance` (last 7 days)

### **Bottom Row - Activity & Details**
```
┌─────────────────────────────────────────────────────────┐
│                    Recent Activity Table               │
│  [Table: event_date, event_name, user_id, site, status]│
│  [Filtered to last 24 hours, limit 50 rows]           │
└─────────────────────────────────────────────────────────┘
```

**Data Source:** `events_flat` (last 24 hours)

## 📈 **Detailed Charts Configuration**

### **1. North Star Metric Scorecard**
- **Data Source:** `v_nsm_daily`
- **Metric:** `nsm_count`
- **Comparison:** Previous period
- **Format:** Number
- **Color:** Green when increasing

### **2. User Growth Line Chart**
- **Data Source:** `v_dau`
- **X-Axis:** `event_date`
- **Y-Axis:** `dau`
- **Time Range:** Last 30 days
- **Trend Line:** Enabled
- **Color:** Blue (#4285F4)

### **3. Performance Metrics Line Chart**
- **Data Source:** `v_latency_daily`
- **X-Axis:** `event_date`
- **Y-Axis:** `p50_ms`, `p75_ms`, `p90_ms`
- **Multiple Lines:** Yes
- **Colors:** 
  - P50: Green (#34A853)
  - P75: Yellow (#FBBC04)
  - P90: Orange (#FF9800)

### **4. Site Performance Bar Chart**
- **Data Source:** `v_site_performance`
- **X-Axis:** `site`
- **Y-Axis:** `success_rate_percent`
- **Sort:** Descending by success rate
- **Color:** Green gradient
- **Time Range:** Last 7 days

### **5. Recent Activity Table**
- **Data Source:** `events_flat`
- **Columns:** 
  - `event_date` (Date)
  - `event_name` (Text)
  - `user_id` (Text)
  - `site` (Text)
  - `status` (Text)
- **Sort:** `event_date` DESC
- **Limit:** 50 rows
- **Time Range:** Last 24 hours

## 🔧 **Dashboard Filters**

### **Date Range Filter**
- **Type:** Date Range
- **Default:** Last 30 days
- **Apply to:** All charts

### **Site Filter**
- **Type:** Dropdown
- **Source:** `events_flat.site`
- **Apply to:** Performance charts, activity table

### **Event Type Filter**
- **Type:** Dropdown
- **Source:** `events_flat.event_name`
- **Apply to:** Activity table

## 🎨 **Styling Guidelines**

### **Color Palette**
- Primary Blue: #4285F4
- Success Green: #34A853
- Warning Yellow: #FBBC04
- Error Red: #EA4335
- Neutral Gray: #9AA0A6

### **Typography**
- Headers: Roboto, 18-24px, Bold
- Body: Roboto, 12-14px, Regular
- Metrics: Roboto, 24-36px, Bold

### **Layout**
- Margins: 16px
- Padding: 8px
- Grid: 12-column responsive

## 📱 **Mobile Optimization**

### **Responsive Breakpoints**
- Desktop: 1200px+
- Tablet: 768px-1199px
- Mobile: <768px

### **Mobile Adjustments**
- Stack charts vertically
- Reduce font sizes by 20%
- Increase touch targets to 44px
- Simplify filters to essential only

## 🔄 **Refresh Settings**

### **Data Refresh**
- **Frequency:** Every hour
- **Time:** On the hour
- **Cache:** 15 minutes

### **Dashboard Refresh**
- **Auto-refresh:** Every 15 minutes
- **Manual refresh:** Available
- **Last updated:** Displayed in footer

## 📊 **Additional Views**

### **Operations Dashboard**
- Detailed error analysis
- Qdrant performance metrics
- Job status monitoring
- System health indicators

### **Marketing Dashboard**
- Traffic source analysis
- UTM campaign performance
- User acquisition metrics
- Conversion funnel analysis

### **Technical Dashboard**
- API performance metrics
- Error rates by type
- Database performance
- Infrastructure metrics

## 🎯 **Success Metrics**

Track these key indicators:

1. **North Star Metric:** >100 daily satisfied answers
2. **User Growth:** >10% week-over-week
3. **Performance:** P50 < 2000ms
4. **Quality:** Success rate > 90%
5. **Engagement:** Conversion rate > 80%

This template provides a solid foundation for your AskBucky analytics dashboard! 