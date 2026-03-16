-- URL Sources table: user-added product URLs to track
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

create table if not exists url_sources (
  id          uuid primary key default gen_random_uuid(),
  label       text not null,
  url         text not null,
  is_active   boolean default true,
  created_at  timestamptz default now()
);

alter table url_sources enable row level security;

create policy "Allow all access to url_sources" on url_sources
  for all using (true) with check (true);
