-- Review with the database owner before running in Supabase SQL Editor.
-- Add the only two values the app will persist from a birthday.
BEGIN;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS horoscope TEXT;
COMMIT;

-- Historical age/horoscope addition. Birthday storage has since been restored
-- by 003_restore_birthday.sql; do not drop the birthday column.
