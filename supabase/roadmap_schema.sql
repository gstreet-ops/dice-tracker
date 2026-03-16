-- Roadmap votes table
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

create table if not exists roadmap_votes (
  id    text primary key,
  votes integer default 0
);

alter table roadmap_votes enable row level security;

create policy "Allow all access to roadmap_votes" on roadmap_votes
  for all using (true) with check (true);
