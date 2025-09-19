{{
  config(
    materialized='view',
    description='Staging view for occupancy data with time-based features'
  )
}}

-- Mock occupancy data - replace with actual occupancy/utilization tables
select
    location_id,
    zone_id,
    ts,
    date(ts at time zone '{{ var("local_timezone") }}') as local_date,
    extract(hour from ts at time zone '{{ var("local_timezone") }}') as local_hour,
    extract(dow from ts at time zone '{{ var("local_timezone") }}') as dow,

    -- Daypart classification
    case
        when extract(hour from ts at time zone '{{ var("local_timezone") }}')
             between {{ var("morning_start_hour") }} and {{ var("morning_end_hour") }} - 1
        then 'morning'
        else 'evening'
    end as daypart,

    -- Occupancy metrics
    total_spaces,
    occupied_spaces,
    available_spaces,
    occupancy_pct,

    -- Demand indicators
    case
        when occupancy_pct >= 0.9 then 'very_high'
        when occupancy_pct >= 0.75 then 'high'
        when occupancy_pct >= 0.5 then 'medium'
        when occupancy_pct >= 0.25 then 'low'
        else 'very_low'
    end as demand_level,

    current_timestamp as loaded_at

from (
    -- Synthetic hourly occupancy data
    select
        ('{' ||
         substr(md5(random()::text), 1, 8) || '-' ||
         substr(md5(random()::text), 1, 4) || '-' ||
         substr(md5(random()::text), 1, 4) || '-' ||
         substr(md5(random()::text), 1, 4) || '-' ||
         substr(md5(random()::text), 1, 12) ||
         '}')::uuid as location_id,
        'z-' || (100 + (random() * 900)::int) as zone_id,
        ts,
        50 as total_spaces,
        (random() * 50)::int as occupied_spaces,
        50 - (random() * 50)::int as available_spaces,
        (random() * 50)::int / 50.0 as occupancy_pct
    from (
        select
            generate_series(
                current_date - interval '30 days',
                current_date,
                interval '1 hour'
            ) as ts
    ) time_series
) synthetic_occupancy

-- In production:
-- from occupancy_snapshots o
-- join locations l on o.location_id = l.id
-- where o.ts >= current_date - interval '90 days'