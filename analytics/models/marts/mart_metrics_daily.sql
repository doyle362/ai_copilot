{{
  config(
    materialized='table',
    description='Daily aggregated metrics by zone for Level Analyst'
  )
}}

with daily_transactions as (
    select
        location_id,
        zone_id,
        date(started_at at time zone '{{ var("local_timezone") }}') as date,
        count(*) as transaction_count,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_ticket,
        avg(duration_minutes) as avg_duration_minutes,
        avg(rate_per_hour) as avg_hourly_rate,

        -- Revenue by daypart
        sum(case when daypart = 'morning' then total_amount else 0 end) as morning_revenue,
        sum(case when daypart = 'evening' then total_amount else 0 end) as evening_revenue,

        -- Transaction counts by daypart
        sum(case when daypart = 'morning' then 1 else 0 end) as morning_transactions,
        sum(case when daypart = 'evening' then 1 else 0 end) as evening_transactions,

        -- Duration analysis
        percentile_cont(0.5) within group (order by duration_minutes) as median_duration_minutes,
        percentile_cont(0.25) within group (order by duration_minutes) as p25_duration_minutes,
        percentile_cont(0.75) within group (order by duration_minutes) as p75_duration_minutes

    from {{ ref('stg_transactions') }}
    group by location_id, zone_id, date
),

daily_occupancy as (
    select
        location_id,
        zone_id,
        local_date as date,
        avg(occupancy_pct) as avg_occupancy_pct,
        max(occupancy_pct) as peak_occupancy_pct,
        min(occupancy_pct) as min_occupancy_pct,

        -- Occupancy by daypart
        avg(case when daypart = 'morning' then occupancy_pct end) as morning_occupancy_pct,
        avg(case when daypart = 'evening' then occupancy_pct end) as evening_occupancy_pct,

        -- High demand hours (>75% occupancy)
        sum(case when occupancy_pct > 0.75 then 1 else 0 end) as high_demand_hours,
        sum(case when occupancy_pct > 0.90 then 1 else 0 end) as very_high_demand_hours

    from {{ ref('stg_occupancy') }}
    group by location_id, zone_id, local_date
)

select
    coalesce(t.location_id, o.location_id) as location_id,
    coalesce(t.zone_id, o.zone_id) as zone_id,
    coalesce(t.date, o.date) as date,

    -- Transaction metrics
    coalesce(t.transaction_count, 0) as transaction_count,
    coalesce(t.total_revenue, 0) as rev,
    coalesce(t.avg_ticket, 0) as avg_ticket,
    coalesce(t.avg_duration_minutes, 0) as avg_duration_minutes,
    coalesce(t.avg_hourly_rate, 0) as avg_hourly_rate,

    -- Daypart revenue split
    coalesce(t.morning_revenue, 0) as morning_revenue,
    coalesce(t.evening_revenue, 0) as evening_revenue,
    case
        when coalesce(t.total_revenue, 0) > 0
        then coalesce(t.morning_revenue, 0) / t.total_revenue
        else 0
    end as morning_revenue_pct,

    -- Transaction split
    coalesce(t.morning_transactions, 0) as morning_transactions,
    coalesce(t.evening_transactions, 0) as evening_transactions,

    -- Duration analysis
    coalesce(t.median_duration_minutes, 0) as median_duration_minutes,
    coalesce(t.p25_duration_minutes, 0) as p25_duration_minutes,
    coalesce(t.p75_duration_minutes, 0) as p75_duration_minutes,

    -- Occupancy metrics
    coalesce(o.avg_occupancy_pct, 0) as occupancy_pct,
    coalesce(o.peak_occupancy_pct, 0) as peak_occupancy_pct,
    coalesce(o.min_occupancy_pct, 0) as min_occupancy_pct,

    coalesce(o.morning_occupancy_pct, 0) as morning_occupancy_pct,
    coalesce(o.evening_occupancy_pct, 0) as evening_occupancy_pct,

    coalesce(o.high_demand_hours, 0) as high_demand_hours,
    coalesce(o.very_high_demand_hours, 0) as very_high_demand_hours,

    -- Performance indicators
    case
        when coalesce(o.avg_occupancy_pct, 0) > 0.8 and coalesce(t.total_revenue, 0) > 100
        then 'high_performance'
        when coalesce(o.avg_occupancy_pct, 0) > 0.5 and coalesce(t.total_revenue, 0) > 50
        then 'good_performance'
        when coalesce(o.avg_occupancy_pct, 0) > 0.25
        then 'moderate_performance'
        else 'low_performance'
    end as performance_tier,

    -- Revenue per occupied space-hour (efficiency metric)
    case
        when coalesce(o.avg_occupancy_pct, 0) > 0
        then coalesce(t.total_revenue, 0) / (o.avg_occupancy_pct * 24)
        else 0
    end as revenue_per_occupied_space_hour,

    current_timestamp as created_at

from daily_transactions t
full outer join daily_occupancy o
    on t.location_id = o.location_id
    and t.zone_id = o.zone_id
    and t.date = o.date

where coalesce(t.date, o.date) >= current_date - interval '90 days'