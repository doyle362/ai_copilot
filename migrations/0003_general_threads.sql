-- Add thread_type column to support general threads
alter table insight_threads
add column if not exists thread_type text default 'insight';

-- Allow nullable insight_id for general threads
alter table insight_threads
alter column insight_id drop not null;

-- Allow nullable zone_id for general threads
alter table insight_threads
alter column zone_id drop not null;

-- Add check constraint for thread types
alter table insight_threads
add constraint thread_type_check check (thread_type in ('insight', 'general'));

-- Add constraint that insight threads must have insight_id and zone_id
alter table insight_threads
add constraint insight_thread_requirements check (
  (thread_type = 'general') or
  (thread_type = 'insight' and insight_id is not null and zone_id is not null)
);

-- Update RLS policies to handle general threads
drop policy if exists threads_read_zone on insight_threads;
drop policy if exists threads_write_zone on insight_threads;

-- Read policy: users can read insight threads for their zones OR general threads
create policy threads_read_zone on insight_threads
for select using (
  thread_type = 'general' or
  (thread_type = 'insight' and exists (
    select 1 from json_array_elements_text(current_setting('jwt.claims.zone_ids', true)::json) as j(z)
    where j.z = insight_threads.zone_id)
  )
);

-- Write policy: users can create/update insight threads for their zones OR general threads
create policy threads_write_zone on insight_threads
for all using (
  thread_type = 'general' or
  (thread_type = 'insight' and exists (
    select 1 from json_array_elements_text(current_setting('jwt.claims.zone_ids', true)::json) as j(z)
    where j.z = insight_threads.zone_id)
  )
);

-- Update thread messages policies to handle general threads
drop policy if exists thread_messages_read on thread_messages;
drop policy if exists thread_messages_write on thread_messages;

create policy thread_messages_read on thread_messages
for select using (
  exists (
    select 1 from insight_threads t
    where t.id = thread_messages.thread_id
    and (
      t.thread_type = 'general' or
      (t.thread_type = 'insight' and exists (
        select 1 from json_array_elements_text(current_setting('jwt.claims.zone_ids', true)::json) as j(z)
        where j.z = t.zone_id)
      )
    )
  )
);

create policy thread_messages_write on thread_messages
for all using (
  exists (
    select 1 from insight_threads t
    where t.id = thread_messages.thread_id
    and (
      t.thread_type = 'general' or
      (t.thread_type = 'insight' and exists (
        select 1 from json_array_elements_text(current_setting('jwt.claims.zone_ids', true)::json) as j(z)
        where j.z = t.zone_id)
      )
    )
  )
);

-- Update index to include thread_type
create index if not exists idx_threads_type_zone_created on insight_threads(thread_type, zone_id, created_at desc);