alter table insights enable row level security;
alter table recommendations enable row level security;
alter table price_changes enable row level security;
alter table insight_threads enable row level security;
alter table thread_messages enable row level security;

-- helper expression: zone_ids from jwt
-- SELECT jsonb_array_elements_text(current_setting('request.jwt.claims', true)::jsonb->'zone_ids')

create policy insights_read_zone on insights
for select using (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = insights.zone_id)
);

create policy recommendations_read_zone on recommendations
for select using (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = recommendations.zone_id)
);

create policy recommendations_write_zone on recommendations
for insert with check (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = recommendations.zone_id)
);

create policy price_changes_read_zone on price_changes
for select using (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = price_changes.zone_id)
);

create policy threads_read_zone on insight_threads
for select using (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = insight_threads.zone_id)
);

create policy threads_write_zone on insight_threads
for insert with check (
  exists (
    select 1 from jsonb_array_elements_text(
      current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
    where j.z = insight_threads.zone_id)
);

create policy messages_read_zone on thread_messages
for select using (
  exists (
    select 1 from insight_threads t
    join jsonb_array_elements_text(current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
      on j.z = t.zone_id
    where t.id = thread_messages.thread_id)
);

create policy messages_write_zone on thread_messages
for insert with check (
  exists (
    select 1 from insight_threads t
    join jsonb_array_elements_text(current_setting('request.jwt.claims', true)::jsonb->'zone_ids') j(z)
      on j.z = t.zone_id
    where t.id = thread_messages.thread_id)
);