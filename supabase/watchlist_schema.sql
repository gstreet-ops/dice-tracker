-- Watchlist table: user-defined product categories to search for
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

create table if not exists watchlist (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,              -- e.g. 'Gold Dice', 'Brass Bookends'
  keywords    text not null,              -- one keyword phrase per line
  max_price   numeric,                    -- optional max price filter (USD)
  is_active   boolean default true,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- Enable RLS (match existing project pattern)
alter table watchlist enable row level security;

-- Allow anon key full access (dashboard reads/writes via anon key)
create policy "Allow all access to watchlist" on watchlist
  for all using (true) with check (true);

-- Add watchlist_category column to products table (nullable, for categorizing results)
alter table products add column if not exists watchlist_category text;
