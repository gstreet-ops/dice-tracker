-- dice-tracker settings table
-- Run this in Supabase SQL Editor to add user-editable settings
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

create table if not exists settings (
  key          text primary key,
  value        text not null,
  label        text,
  description  text,
  updated_at   timestamptz default now()
);

-- Default settings
insert into settings (key, value, label, description) values
  ('search_keywords', '50mm gold dice d6 engraved,jumbo gold metal dice 2 inch,brass gold dice 50mm', 'Search keywords', 'Comma-separated search terms used across all sources'),
  ('max_price_usd', '150', 'Max price (USD)', 'Maximum price to consider — products above this are ignored'),
  ('min_size_mm', '50', 'Minimum size (mm)', 'Minimum die size in millimeters (50mm = 2 inches)'),
  ('run_frequency_hours', '6', 'Search frequency (hours)', 'How often the tracker searches — 6 = every 6 hours')
on conflict (key) do nothing;
