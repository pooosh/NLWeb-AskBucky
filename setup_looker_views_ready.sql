-- AskBucky Looker Studio Dashboard Views (Ready to Execute)
-- Execute this once your application is deployed and events are flowing

-- ============================================================================
-- MAIN FLAT EVENT VIEW
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.events_flat` AS
SELECT
  TIMESTAMP(jsonPayload.event_time)                AS event_ts,
  DATE(TIMESTAMP(jsonPayload.event_time))          AS event_date,
  jsonPayload.event_name                           AS event_name,
  jsonPayload.user_id                              AS user_id,
  jsonPayload.session_id                           AS session_id,
  SAFE_CAST(jsonPayload.props.latency_ms AS INT64) AS latency_ms,
  SAFE_CAST(jsonPayload.props.sources_count AS INT64) AS sources_count,
  jsonPayload.props.status                         AS status,
  jsonPayload.props.site                           AS site,
  jsonPayload.props.sitetag                        AS sitetag,
  jsonPayload.props.model                          AS model,
  jsonPayload.props.utm_source                     AS utm_source,
  jsonPayload.props.utm_medium                     AS utm_medium,
  jsonPayload.props.utm_campaign                   AS utm_campaign,
  jsonPayload.props.query                          AS query,
  SAFE_CAST(jsonPayload.props.query_len AS INT64) AS query_len,
  jsonPayload.props.error_type                     AS error_type,
  jsonPayload.props.error_message                  AS error_message,
  jsonPayload.props.job_name                       AS job_name,
  SAFE_CAST(jsonPayload.props.duration_ms AS INT64) AS duration_ms,
  SAFE_CAST(jsonPayload.props.records_processed AS INT64) AS records_processed,
  SAFE_CAST(jsonPayload.props.hits_count AS INT64) AS hits_count,
  SAFE_CAST(jsonPayload.props.total_points AS INT64) AS total_points,
  SAFE_CAST(jsonPayload.props.hit_rate AS FLOAT64) AS hit_rate,
  SAFE_CAST(jsonPayload.props.search_time_ms AS INT64) AS search_time_ms,
  jsonPayload.props.collection_name                AS collection_name
FROM `askbucky-469317.askbucky_analytics._AllLogs`
WHERE jsonPayload.type = 'event';

-- ============================================================================
-- DAILY LATENCY VIEW (P50)
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.v_latency_daily` AS
SELECT
  event_date,
  APPROX_QUANTILES(latency_ms, 2)[OFFSET(1)] AS p50_ms,
  APPROX_QUANTILES(latency_ms, 4)[OFFSET(3)] AS p75_ms,
  APPROX_QUANTILES(latency_ms, 10)[OFFSET(9)] AS p90_ms,
  AVG(latency_ms) AS avg_ms,
  COUNT(*) AS total_requests
FROM `askbucky-469317.askbucky_analytics.events_flat`
WHERE event_name = 'ask_answered' 
  AND latency_ms IS NOT NULL
  AND latency_ms > 0
GROUP BY event_date
ORDER BY event_date;

-- ============================================================================
-- NORTH STAR METRIC VIEW
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.v_nsm_daily` AS
SELECT
  event_date,
  COUNTIF(event_name='ask_answered'
          AND status='success'
          AND COALESCE(sources_count,0) >= 1
          AND COALESCE(latency_ms, 999999) <= 3000) AS nsm_count,
  COUNTIF(event_name='ask_answered') AS total_answers,
  SAFE_DIVIDE(
    COUNTIF(event_name='ask_answered'
            AND status='success'
            AND COALESCE(sources_count,0) >= 1
            AND COALESCE(latency_ms, 999999) <= 3000),
    COUNTIF(event_name='ask_answered')
  ) * 100 AS nsm_percentage
FROM `askbucky-469317.askbucky_analytics.events_flat`
GROUP BY event_date
ORDER BY event_date;

-- ============================================================================
-- DAILY ACTIVE USERS VIEW
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.v_dau` AS
SELECT
  event_date,
  COUNT(DISTINCT user_id) AS dau
FROM `askbucky-469317.askbucky_analytics.events_flat`
WHERE event_name IN ('page_view', 'ask_answered')
GROUP BY event_date
ORDER BY event_date;

-- ============================================================================
-- LIFETIME UNIQUE USERS VIEW
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.v_lifetime_users` AS
WITH first_seen AS (
  SELECT
    user_id,
    MIN(event_date) AS first_day
  FROM `askbucky-469317.askbucky_analytics.events_flat`
  WHERE event_name IN ('page_view', 'ask_answered')
  GROUP BY user_id
),
days AS (
  SELECT day
  FROM UNNEST(GENERATE_DATE_ARRAY(
    (SELECT MIN(first_day) FROM first_seen),
    CURRENT_DATE()
  )) AS day
)
SELECT
  d.day AS event_date,
  COUNTIF(f.first_day <= d.day) AS lifetime_unique_users
FROM days d
LEFT JOIN first_seen f ON TRUE
GROUP BY d.day
ORDER BY d.day;

-- ============================================================================
-- CONVERSION RATE VIEW
-- ============================================================================
CREATE OR REPLACE VIEW `askbucky-469317.askbucky_analytics.v_conversion_daily` AS
WITH sessions AS (
  SELECT
    session_id,
    event_date,
    MAX(IF(event_name='ask_answered' AND status='success', 1, 0)) AS converted
  FROM `askbucky-469317.askbucky_analytics.events_flat`
  GROUP BY session_id, event_date
)
SELECT
  event_date,
  COUNT(*) AS total_sessions,
  SUM(converted) AS converted_sessions,
  SAFE_DIVIDE(SUM(converted), COUNT(*)) * 100 AS conversion_rate_percent
FROM sessions
GROUP BY event_date
ORDER BY event_date; 