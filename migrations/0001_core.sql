create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists insights(
  id uuid primary key default gen_random_uuid(),
  location_id uuid,
  zone_id text not null,
  kind text,
  "window" text,
  metrics_json jsonb,
  narrative_text text,
  confidence numeric,
  created_at timestamptz default now(),
  created_by uuid
);

create table if not exists recommendations(
  id uuid primary key default gen_random_uuid(),
  location_id uuid,
  zone_id text not null,
  type text,
  proposal jsonb,
  rationale_text text,
  expected_lift_json jsonb,
  confidence numeric,
  requires_approval boolean default true,
  memory_ids_used bigint[] default '{}',
  prompt_version_id bigint,
  thread_id bigint,
  status text default 'draft',
  created_at timestamptz default now()
);

create table if not exists price_changes(
  id uuid primary key default gen_random_uuid(),
  location_id uuid,
  zone_id text not null,
  prev_price numeric,
  new_price numeric,
  change_pct numeric,
  policy_version text,
  recommendation_id uuid,
  applied_by uuid,
  applied_at timestamptz,
  revert_to numeric,
  revert_if jsonb,
  expires_at timestamptz,
  status text default 'pending',
  created_at timestamptz default now()
);

create table if not exists insight_threads(
  id bigserial primary key,
  insight_id uuid references insights(id) on delete cascade,
  zone_id text not null,
  status text default 'open',
  created_at timestamptz default now()
);

create table if not exists thread_messages(
  id bigserial primary key,
  thread_id bigint references insight_threads(id) on delete cascade,
  role text check (role in ('user','ai','system')) not null,
  content text not null,
  meta jsonb,
  created_by uuid,
  created_at timestamptz default now()
);

create table if not exists agent_prompt_versions(
  id bigserial primary key,
  scope text check (scope in ('global','client','location','zone')) not null,
  scope_ref uuid,
  version int not null,
  title text,
  system_prompt text not null,
  created_by uuid,
  created_at timestamptz default now(),
  is_active boolean default false
);
create unique index if not exists agent_prompt_versions_active_one
  on agent_prompt_versions(scope, scope_ref, is_active) where is_active;

create table if not exists agent_guardrails(
  id bigserial primary key,
  name text not null,
  json_schema jsonb not null,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists feedback_memories(
  id bigserial primary key,
  scope text check (scope in ('global','client','location','zone')) not null,
  scope_ref uuid,
  topic text,
  kind text check (kind in ('canonical','context','exception')) not null,
  content text not null,
  source_thread_id bigint references insight_threads(id),
  expires_at timestamptz,
  created_by uuid,
  created_at timestamptz default now(),
  is_active boolean default true
);

create table if not exists feedback_memory_embeddings(
  memory_id bigint primary key references feedback_memories(id) on delete cascade,
  embedding vector(1536)
);

-- marts (minimal)
create table if not exists mart_metrics_daily(
  date date,
  location_id uuid,
  zone_id text,
  rev numeric,
  occupancy_pct numeric,
  avg_ticket numeric
);
create table if not exists mart_metrics_hourly(
  ts timestamptz,
  location_id uuid,
  zone_id text,
  rev numeric,
  occupancy_pct numeric,
  avg_ticket numeric
);

-- inferred/proposed rate plans (computed pricing)
create table if not exists inferred_rate_plans(
  id uuid primary key default gen_random_uuid(),
  location_id uuid not null,
  zone_id text not null,
  daypart text check (daypart in ('morning','evening')) not null,
  dow int check (dow between 0 and 6) not null,
  tiers jsonb not null,
  source text default 'analysis',
  created_at timestamptz default now()
);

create table if not exists proposed_rate_plans(
  id uuid primary key default gen_random_uuid(),
  recommendation_id uuid references recommendations(id) on delete cascade,
  location_id uuid not null,
  zone_id text not null,
  daypart text not null,
  dow int not null,
  tiers jsonb not null,
  expected_lift_json jsonb,
  rationale_text text,
  confidence numeric,
  created_at timestamptz default now()
);

-- helpful indexes
create index if not exists idx_insights_zone_created on insights(zone_id, created_at desc);
create index if not exists idx_recs_zone_created on recommendations(zone_id, created_at desc);
create index if not exists idx_price_changes_zone_created on price_changes(zone_id, created_at desc);
create index if not exists idx_threads_zone_created on insight_threads(zone_id, created_at desc);
create index if not exists idx_memories_scope_active on feedback_memories(scope, scope_ref, is_active);
create index if not exists idx_mart_daily_zone_date on mart_metrics_daily(zone_id, date desc);
create index if not exists idx_inferred_rate_plans_zone on inferred_rate_plans(zone_id);

-- seed a global prompt v1 and default guardrails
insert into agent_prompt_versions(scope, scope_ref, version, title, system_prompt, is_active)
values ('global', null, 1, 'Global v1',
'You are "Level Analyst", an AI optimization copilot for Level Parking. Be precise, safe, and explainable.
OUTPUT: valid JSON per provided schema. Respect GUARDRAILS and PRIOR FEEDBACK. If confidence<0.6, ask questions.',
true);

insert into agent_guardrails(name, json_schema) values
('default-guardrails', '{
  "max_change_pct": 0.15,
  "min_price": 2.0,
  "blackout_weekday_hours": {"fri":[16,17,18,19]},
  "require_approval_if_confidence_lt": 0.7
}');