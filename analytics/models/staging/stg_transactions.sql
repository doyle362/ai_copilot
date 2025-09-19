{{
  config(
    materialized='view',
    description='Staging view for transaction/stay data with calculated fields'
  )
}}

-- Using the actual historical_transactions table
select
    id as transaction_id,
    null::uuid as location_id, -- location_id not available in historical table
    'z-' || zone::text as zone_id,
    (start_park_date + start_park_time)::timestamp as started_at,
    (stop_park_date + stop_park_time)::timestamp as ended_at,
    coalesce(paid_minutes, 0) as duration_minutes,
    coalesce(
        case
            when payment_amount ~ '^\$?[0-9]+\.?[0-9]*$'
            then replace(payment_amount, '$', '')::numeric
            else 0
        end,
        0
    ) as total_amount,
    coalesce(
        case
            when payment_amount ~ '^\$?[0-9]+\.?[0-9]*$' and paid_minutes > 0
            then (replace(payment_amount, '$', '')::numeric * 60 / paid_minutes)
            else 0
        end,
        0
    ) as rate_per_hour,

    -- Add time-based features
    extract(hour from (start_park_date + start_park_time) at time zone '{{ var("local_timezone") }}') as local_hour,
    extract(dow from (start_park_date + start_park_time) at time zone '{{ var("local_timezone") }}') as dow, -- 0=Sunday

    -- Calculate daypart
    case
        when extract(hour from (start_park_date + start_park_time) at time zone '{{ var("local_timezone") }}')
             between {{ var("morning_start_hour") }} and {{ var("morning_end_hour") }} - 1
        then 'morning'
        else 'evening'
    end as daypart,

    -- Calculate rate tier (simplified)
    case
        when coalesce(paid_minutes, 0) <= 60 then 'first_hour'
        when coalesce(paid_minutes, 0) <= 180 then 'short_stay'
        else 'long_stay'
    end as rate_tier,

    current_timestamp as loaded_at

from {{ source('public', 'historical_transactions') }}
where start_park_date >= current_date - interval '90 days'
  and stop_park_date is not null
  and payment_amount is not null
  and payment_amount != ''
  and zone is not null