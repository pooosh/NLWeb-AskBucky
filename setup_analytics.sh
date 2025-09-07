#!/bin/bash

# AskBucky Analytics Setup Script
# This script sets up BigQuery infrastructure for analytics tracking

set -e

# Configuration
PROJECT_ID="askbucky-469317"
DATASET_NAME="askbucky_analytics"
TABLE_NAME="events"
SINK_NAME="events-to-bq"

echo "Setting up AskBucky Analytics Infrastructure..."
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET_NAME"
echo "Table: $TABLE_NAME"
echo "Sink: $SINK_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if bq is installed
if ! command -v bq &> /dev/null; then
    echo "Error: BigQuery CLI (bq) is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/bigquery/docs/bq-command-line-tool"
    exit 1
fi

# Set the project
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Create BigQuery dataset
echo "Creating BigQuery dataset..."
bq --location=US mk -d $PROJECT_ID:$DATASET_NAME

# Create log sink to BigQuery
echo "Creating log sink to BigQuery..."
gcloud logging sinks create $SINK_NAME \
  bigquery.googleapis.com/projects/$PROJECT_ID/datasets/$DATASET_NAME \
  --log-filter='resource.type="cloud_run_revision"
                AND resource.labels.service_name="askbucky"
                AND jsonPayload.type="event"'

# Get the sink service account
echo "Getting sink service account..."
SINK_SA=$(gcloud logging sinks describe $SINK_NAME --format='value(writerIdentity)')
echo "Sink service account: $SINK_SA"

# Grant sink service account permission to write to BigQuery
echo "Granting BigQuery write permissions..."
bq add-iam-policy-binding $PROJECT_ID:$DATASET_NAME \
  --member="$SINK_SA" \
  --role="roles/bigquery.dataEditor"

echo ""
echo "✅ Analytics infrastructure setup complete!"
echo ""
echo "Next steps:"
echo "1. Deploy your updated AskBucky application to Cloud Run"
echo "2. Events will automatically be streamed to BigQuery"
echo "3. Use the SQL queries in analytics_queries.sql to analyze your data"
echo ""
echo "To view your events in BigQuery:"
echo "bq query --use_legacy_sql=false 'SELECT * FROM \`$PROJECT_ID.$DATASET_NAME._AllLogs\` LIMIT 10'"
echo ""
echo "To check if events are flowing:"
echo "bq query --use_legacy_sql=false 'SELECT COUNT(*) as event_count FROM \`$PROJECT_ID.$DATASET_NAME._AllLogs\` WHERE jsonPayload.type=\"event\"'" 