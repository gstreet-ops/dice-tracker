-- dice-tracker Supabase schema
-- Run this once in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

-- Products table: one row per unique product URL
create table if not exists products (
  id           uuid primary key default gen_random_uuid(),
  source       text not null,         -- 'chessex' | 'ebay' | 'google_shopping' | 'aliexpress' | 'etsy'
  title        text not null,
  url          text not null unique,
  image_url    text,
  size_mm      numeric,               -- extracted or estimated die size in mm
  material     text,                  -- 'resin' | 'metal' | 'zinc_alloy' | 'brass' | 'unknown'
  finish       text,                  -- 'gold' | 'gold_glitter' | 'gold_pips_only' | 'unknown'
  pip_style    text,                  -- 'engraved' | 'printed' | 'unknown'
  set_count    integer,               -- number of dice in set (2, 3, etc.)
  score        integer default 0,     -- quality match score 0-100
  is_excluded  boolean default false, -- manually excluded
  first_seen   timestamptz default now(),
  last_seen    timestamptz default now(),
  created_at   timestamptz default now()
);

-- Price history table: one row per scrape per product
create table if not exists price_history (
  id            uuid primary key default gen_random_uuid(),
  product_id    uuid references products(id) on delete cascade,
  price_usd     numeric not null,
  currency_orig text default 'USD',
  price_orig    numeric,
  in_stock      boolean default true,
  scraped_at    timestamptz default now()
);

-- Run log table: one row per scraper run
create table if not exists run_log (
  id           uuid primary key default gen_random_uuid(),
  ran_at       timestamptz default now(),
  source       text,
  results_found integer default 0,
  new_products  integer default 0,
  price_drops   integer default 0,
  errors        text,
  duration_secs numeric
);

-- Indexes for fast dashboard queries
create index if not exists idx_price_history_product on price_history(product_id);
create index if not exists idx_price_history_scraped on price_history(scraped_at desc);
create index if not exists idx_products_score on products(score desc);
create index if not exists idx_products_source on products(source);
create index if not exists idx_products_last_seen on products(last_seen desc);

-- Keepalive table (prevents Supabase free tier pause)
create table if not exists keepalive (
  id        serial primary key,
  pinged_at timestamptz default now()
);
insert into keepalive default values;
