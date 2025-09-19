{{
  config(
    materialized='table',
    description='Feature inputs for rate inference analysis'
  )
}}

with transaction_features as (
    select
        location_id,
        zone_id,
        date(started_at at time zone '{{ var("local_timezone") }}') as date,
        daypart,
        dow,

        -- Duration distribution features
        count(*) as transaction_count,
        avg(duration_minutes) as avg_duration,
        percentile_cont(0.25) within group (order by duration_minutes) as p25_duration,
        percentile_cont(0.5) within group (order by duration_minutes) as median_duration,
        percentile_cont(0.75) within group (order by duration_minutes) as p75_duration,
        percentile_cont(0.9) within group (order by duration_minutes) as p90_duration,
        max(duration_minutes) as max_duration,

        -- Revenue features
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_transaction_amount,
        avg(rate_per_hour) as avg_observed_rate,
        percentile_cont(0.5) within group (order by rate_per_hour) as median_observed_rate,

        -- Duration tier distribution
        sum(case when duration_minutes <= 60 then 1 else 0 end) as short_stays_count,
        sum(case when duration_minutes between 61 and 180 then 1 else 0 end) as medium_stays_count,
        sum(case when duration_minutes > 180 then 1 else 0 end) as long_stays_count,

        -- Revenue by duration tier
        sum(case when duration_minutes <= 60 then total_amount else 0 end) as short_stays_revenue,
        sum(case when duration_minutes between 61 and 180 then total_amount else 0 end) as medium_stays_revenue,
        sum(case when duration_minutes > 180 then total_amount else 0 end) as long_stays_revenue,

        -- Rate by duration tier
        avg(case when duration_minutes <= 60 then rate_per_hour end) as short_stays_avg_rate,
        avg(case when duration_minutes between 61 and 180 then rate_per_hour end) as medium_stays_avg_rate,
        avg(case when duration_minutes > 180 then rate_per_hour end) as long_stays_avg_rate

    from {{ ref('stg_transactions') }}
    where started_at >= current_date - interval '90 days'
    group by location_id, zone_id, date, daypart, dow
),

occupancy_context as (
    select
        location_id,
        zone_id,
        local_date as date,
        daypart,
        dow,

        avg(occupancy_pct) as avg_occupancy_pct,
        max(occupancy_pct) as peak_occupancy_pct,
        count(case when occupancy_pct > 0.8 then 1 end) as high_demand_periods

    from {{ ref('stg_occupancy') }}
    where ts >= current_date - interval '90 days'
    group by location_id, zone_id, local_date, daypart, dow
),

combined_features as (
    select
        coalesce(t.location_id, o.location_id) as location_id,
        coalesce(t.zone_id, o.zone_id) as zone_id,
        coalesce(t.date, o.date) as date,
        coalesce(t.daypart, o.daypart) as daypart,
        coalesce(t.dow, o.dow) as dow,

        -- Transaction features
        coalesce(t.transaction_count, 0) as transaction_count,
        coalesce(t.avg_duration, 0) as avg_duration_minutes,
        coalesce(t.median_duration, 0) as median_duration_minutes,
        coalesce(t.p25_duration, 0) as p25_duration_minutes,
        coalesce(t.p75_duration, 0) as p75_duration_minutes,
        coalesce(t.p90_duration, 0) as p90_duration_minutes,
        coalesce(t.max_duration, 0) as max_duration_minutes,

        coalesce(t.total_revenue, 0) as total_revenue,
        coalesce(t.avg_transaction_amount, 0) as avg_transaction_amount,
        coalesce(t.avg_observed_rate, 0) as avg_observed_hourly_rate,
        coalesce(t.median_observed_rate, 0) as median_observed_hourly_rate,

        -- Duration tier counts and revenue
        coalesce(t.short_stays_count, 0) as short_stays_count,
        coalesce(t.medium_stays_count, 0) as medium_stays_count,
        coalesce(t.long_stays_count, 0) as long_stays_count,

        coalesce(t.short_stays_revenue, 0) as short_stays_revenue,
        coalesce(t.medium_stays_revenue, 0) as medium_stays_revenue,
        coalesce(t.long_stays_revenue, 0) as long_stays_revenue,

        coalesce(t.short_stays_avg_rate, 0) as short_stays_avg_rate,
        coalesce(t.medium_stays_avg_rate, 0) as medium_stays_avg_rate,
        coalesce(t.long_stays_avg_rate, 0) as long_stays_avg_rate,

        -- Distribution percentages
        case
            when coalesce(t.transaction_count, 0) > 0
            then coalesce(t.short_stays_count, 0)::float / t.transaction_count
            else 0
        end as short_stays_pct,

        case
            when coalesce(t.transaction_count, 0) > 0
            then coalesce(t.medium_stays_count, 0)::float / t.transaction_count
            else 0
        end as medium_stays_pct,

        case
            when coalesce(t.transaction_count, 0) > 0
            then coalesce(t.long_stays_count, 0)::float / t.transaction_count
            else 0
        end as long_stays_pct,

        -- Occupancy context
        coalesce(o.avg_occupancy_pct, 0) as avg_occupancy_pct,
        coalesce(o.peak_occupancy_pct, 0) as peak_occupancy_pct,
        coalesce(o.high_demand_periods, 0) as high_demand_periods,

        -- Weighted demand metrics (recent data weighted higher)
        COALESCE(w.w_txn, 0) AS w_txn,
        COALESCE(w.w_minutes, 0) AS w_minutes,
        COALESCE(w.w_revenue, 0) AS w_revenue,

        -- Demand pressure indicators
        case
            when coalesce(o.avg_occupancy_pct, 0) > 0.8 then 'very_high'
            when coalesce(o.avg_occupancy_pct, 0) > 0.6 then 'high'
            when coalesce(o.avg_occupancy_pct, 0) > 0.4 then 'medium'
            when coalesce(o.avg_occupancy_pct, 0) > 0.2 then 'low'
            else 'very_low'
        end as demand_pressure,

        -- Revenue efficiency (revenue per unit of demand)
        case
            when coalesce(o.avg_occupancy_pct, 0) > 0
            then coalesce(t.total_revenue, 0) / o.avg_occupancy_pct
            else 0
        end as revenue_efficiency

    from transaction_features t
    full outer join occupancy_context o
        on t.location_id = o.location_id
        and t.zone_id = o.zone_id
        and t.date = o.date
        and t.daypart = o.daypart
        and t.dow = o.dow
    left join {{ ref('mart_demand_weighted') }} w
        on COALESCE(t.zone_id, o.zone_id) = w.zone_id
        and COALESCE(t.date, o.date) = w.date
        and COALESCE(t.daypart, o.daypart) = w.daypart
        and COALESCE(t.dow, o.dow) = w.dow
),

-- Add day type and time context
final_features as (
    select
        *,

        -- Day type classification
        case
            when dow in (0, 6) then 'weekend'
            when dow in (1, 5) then 'weekday_edge'  -- Monday, Friday
            else 'weekday_core'  -- Tuesday, Wednesday, Thursday
        end as day_type,

        -- Seasonal/weekly patterns (would be more sophisticated in production)
        case
            when date_part('week', date) % 4 = 0 then 'peak_week'
            else 'regular_week'
        end as week_type,

        -- Data quality indicators
        case
            when transaction_count >= 10 then 'sufficient'
            when transaction_count >= 3 then 'limited'
            else 'insufficient'
        end as data_sufficiency,

        current_timestamp as created_at

    from combined_features
)

select * from final_features
where date >= current_date - interval '60 days'  -- Keep last 60 days for inference