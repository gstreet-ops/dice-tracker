-- Enable RLS on all dice-tracker tables
-- dice-tracker uses service_role key (bypasses RLS) so scrapers are unaffected
-- This blocks anonymous access via anon key

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixed_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- No policies needed — service_role bypasses RLS
-- If a future dashboard needs anon read access, add:
-- CREATE POLICY "Anon read products" ON products FOR SELECT USING (true);
-- CREATE POLICY "Anon read price_history" ON price_history FOR SELECT USING (true);
