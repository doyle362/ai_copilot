{{
  config(
    materialized='table',
    description='Hourly aggregated metrics by zone for Level Analyst'
  )
}}

with hourly_transactions as (
    select
        location_id,
        zone_id,
        date_trunc('hour', started_at at time zone '{{ var("local_timezone") }}') as hour_ts,
        extract(hour from started_at at time zone '{{ var("local_timezone") }}') as local_hour,
        extract(dow from started_at at time zone '{{ var("local_timezone") }}') as dow,

        case
            when extract(hour from started_at at time zone '{{ var("local_timezone") }}')
                 between {{ var("morning_start_hour") }} and {{ var("morning_end_hour") }} - 1
            then 'morning'
            else 'evening'
        end as daypart,

        count(*) as transaction_count,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_ticket,
        avg(duration_minutes) as avg_duration_minutes,
        avg(rate_per_hour) as avg_hourly_rate,

        -- Duration percentiles
        percentile_cont(0.5) within group (order by duration_minutes) as median_duration_minutes

    from {{ ref('stg_transactions') }}
    group by location_id, zone_id, hour_ts, local_hour, dow, daypart
),

hourly_occupancy as (
    select
        location_id,
        zone_id,
        date_trunc('hour', ts at time zone '{{ var("local_timezone") }}') as hour_ts,
        extract(hour from ts at time zone '{{ var("local_timezone") }}') as local_hour,
        extract(dow from ts at time zone '{{ var("local_timezone") }}') as dow,

        case
            when extract(hour from ts at time zone '{{ var("local_timezone") }}')
                 between {{ var("morning_start_hour") }} and {{ var("morning_end_hour") }} - 1
            then 'morning'
            else 'evening'
        end as daypart,

        avg(occupancy_pct) as avg_occupancy_pct,
        max(occupancy_pct) as peak_occupancy_pct,
        min(occupancy_pct) as min_occupancy_pct

    from {{ ref('stg_occupancy') }}
    group by location_id, zone_id, hour_ts, local_hour, dow, daypart
)

select
    coalesce(t.location_id, o.location_id) as location_id,
    coalesce(t.zone_id, o.zone_id) as zone_id,
    coalesce(t.hour_ts, o.hour_ts) at time zone '{{ var("local_timezone") }}' as ts,
    coalesce(t.local_hour, o.local_hour) as local_hour,
    coalesce(t.dow, o.dow) as dow,
    coalesce(t.daypart, o.daypart) as daypart,

    -- Transaction metrics
    coalesce(t.transaction_count, 0) as transaction_count,
    coalesce(t.total_revenue, 0) as rev,
    coalesce(t.avg_ticket, 0) as avg_ticket,
    coalesce(t.avg_duration_minutes, 0) as avg_duration_minutes,
    coalesce(t.avg_hourly_rate, 0) as avg_hourly_rate,
    coalesce(t.median_duration_minutes, 0) as median_duration_minutes,

    -- Occupancy metrics
    coalesce(o.avg_occupancy_pct, 0) as occupancy_pct,
    coalesce(o.peak_occupancy_pct, 0) as peak_occupancy_pct,
    coalesce(o.min_occupancy_pct, 0) as min_occupancy_pct,

    -- Performance indicators
    case
        when coalesce(o.avg_occupancy_pct, 0) > 0.85 then 'very_high_demand'
        when coalesce(o.avg_occupancy_pct, 0) > 0.70 then 'high_demand'
        when coalesce(o.avg_occupancy_pct, 0) > 0.50 then 'medium_demand'
        when coalesce(o.avg_occupancy_pct, 0) > 0.25 then 'low_demand'
        else 'very_low_demand'
    end as demand_level,

    -- Revenue efficiency
    case
        when coalesce(o.avg_occupancy_pct, 0) > 0
        then coalesce(t.total_revenue, 0) / o.avg_occupancy_pct
        else 0
    end as revenue_per_occupancy_pct,

    -- Hour type classification
    case
        when coalesce(t.local_hour, o.local_hour) between 7 and 9 then 'morning_peak'
        when coalesce(t.local_hour, o.local_hour) between 17 and 19 then 'evening_peak'
        when coalesce(t.local_hour, o.local_hour) between 10 and 16 then 'midday'
        when coalesce(t.local_hour, o.local_hour) between 20 and 23 then 'night'
        else 'overnight'
    end as hour_type,

    -- Weekend vs weekday
    case
        when coalesce(t.dow, o.dow) in (0, 6) then 'weekend'
        else 'weekday'
    end as day_type,

    current_timestamp as created_at

from hourly_transactions t
full outer join hourly_occupancy o
    on t.location_id = o.location_id
    and t.zone_id = o.zone_id
    and t.hour_ts = o.hour_ts

where coalesce(t.hour_ts, o.hour_ts) >= current_timestamp - interval '30 days'