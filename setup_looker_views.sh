#!/bin/bash

# AskBucky Looker Studio Views Setup Script
# This script creates all the BigQuery views needed for Looker Studio dashboard

set -e

echo "🚀 Setting up BigQuery Views for Looker Studio Dashboard..."
echo ""

# Check if bq is available
if ! command -v bq &> /dev/null; then
    echo "❌ Error: BigQuery CLI (bq) is not installed."
    echo "Please install it first: https://cloud.google.com/bigquery/docs/bq-command-line-tool"
    exit 1
fi

# Check if the dataset exists
echo "🔍 Checking if BigQuery dataset exists..."
if ! bq show askbucky-469317:askbucky_analytics &> /dev/null; then
    echo "❌ Error: BigQuery dataset 'askbucky_analytics' not found."
    echo "Please run ./setup_analytics.sh first to create the dataset."
    exit 1
fi

echo "✅ BigQuery dataset found"
echo ""

# Execute the SQL file
echo "📊 Creating BigQuery views..."
echo "This may take a few minutes..."

# Read the SQL file and execute each statement
while IFS= read -r line; do
    # Skip empty lines and comments
    if [[ -z "$line" || "$line" =~ ^-- ]]; then
        continue
    fi
    
    # If line contains CREATE OR REPLACE VIEW, it's a view definition
    if [[ "$line" =~ CREATE.*VIEW ]]; then
        echo "   Creating view: $(echo "$line" | grep -o 'v_[a-zA-Z_]*' || echo 'events_flat')"
    fi
done < setup_looker_views.sql

# Execute the entire SQL file
bq query --use_legacy_sql=false --quiet < setup_looker_views.sql

echo ""
echo "✅ All BigQuery views created successfully!"
echo ""

# List the created views
echo "📋 Created Views:"
echo "   - events_flat (main flat event view)"
echo "   - v_latency_daily (daily latency metrics)"
echo "   - v_nsm_daily (North Star Metric)"
echo "   - v_dau (Daily Active Users)"
echo "   - v_lifetime_users (Lifetime Unique Users)"
echo "   - v_conversion_daily (Conversion Rates)"
echo "   - v_site_performance (Site Performance)"
echo "   - v_traffic_sources (Traffic Sources)"
echo "   - v_errors_daily (Error Analysis)"
echo "   - v_qdrant_performance (Qdrant Performance)"
echo "   - v_job_status (Job Status)"
echo ""

echo "🎯 Next Steps for Looker Studio:"
echo "1. Go to https://lookerstudio.google.com/"
echo "2. Click 'Create' → 'Data Source'"
echo "3. Select 'BigQuery' connector"
echo "4. Choose your project: askbucky-469317"
echo "5. Select dataset: askbucky_analytics"
echo "6. Choose view: events_flat (for main dashboard)"
echo "7. Create your dashboard!"
echo ""

echo "📊 Recommended Dashboard Structure:"
echo "   - Use 'events_flat' as your main data source"
echo "   - Use 'v_nsm_daily' for North Star Metric charts"
echo "   - Use 'v_latency_daily' for performance charts"
echo "   - Use 'v_dau' for user growth charts"
echo "   - Use 'v_lifetime_users' for cumulative user charts"
echo ""

echo "🔗 Quick Links:"
echo "   - Looker Studio: https://lookerstudio.google.com/"
echo "   - BigQuery Console: https://console.cloud.google.com/bigquery?project=askbucky-469317"
echo "   - Dataset: askbucky-469317.askbucky_analytics"
echo ""

echo "🎉 Setup complete! Your BigQuery views are ready for Looker Studio." 