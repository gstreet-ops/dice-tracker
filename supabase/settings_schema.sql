-- Add email alert settings to the settings table
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Project: dice-tracker (zziindzdwzlmnkccenfx)

INSERT INTO settings (key, value) VALUES ('alert_from_email', '')
  ON CONFLICT (key) DO NOTHING;
INSERT INTO settings (key, value) VALUES ('alert_gmail_password', '')
  ON CONFLICT (key) DO NOTHING;
INSERT INTO settings (key, value) VALUES ('alert_to_email', '')
  ON CONFLICT (key) DO NOTHING;
