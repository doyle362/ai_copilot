{{
  config(
    materialized='view',
    indexes=[
      {'columns': ['zone_id', 'date', 'daypart'], 'unique': false}
    ]
  )
}}

WITH daily_transactions AS (
  SELECT
    ts::date AS date,
    zone_id,
    CASE
      WHEN EXTRACT(hour FROM ts) BETWEEN 8 AND 15 THEN 'morning'
      WHEN EXTRACT(hour FROM ts) BETWEEN 16 AND 23 THEN 'evening'
      ELSE NULL
    END AS daypart,
    EXTRACT(dow FROM ts)::int AS dow,
    duration_min,
    amount_usd,
    {{ recency_weight('ts::date') }} AS recency_weight
  FROM {{ ref('stg_transactions') }}
  WHERE EXTRACT(hour FROM ts) BETWEEN 8 AND 23  -- filter valid dayparts
),

aggregated AS (
  SELECT
    date,
    zone_id,
    daypart,
    dow,

    -- Raw totals
    COUNT(*) AS total_txn,
    SUM(duration_min) AS total_minutes,
    SUM(amount_usd) AS total_revenue,

    -- Recency-weighted totals
    SUM(recency_weight) AS weighted_txn,
    SUM(duration_min * recency_weight) AS weighted_minutes,
    SUM(amount_usd * recency_weight) AS weighted_revenue

  FROM daily_transactions
  WHERE daypart IS NOT NULL
  GROUP BY date, zone_id, daypart, dow
)

SELECT
  date,
  zone_id,
  daypart,
  dow,
  total_txn,
  total_minutes,
  total_revenue,
  ROUND(weighted_txn, 2) AS weighted_txn,
  ROUND(weighted_minutes, 2) AS weighted_minutes,
  ROUND(weighted_revenue, 2) AS weighted_revenue
FROM aggregated
ORDER BY zone_id, date DESC, daypart