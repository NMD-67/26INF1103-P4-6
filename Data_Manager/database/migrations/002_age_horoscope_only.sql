-- Review with the database owner before running in Supabase SQL Editor.
-- Add the only two values the app will persist from a birthday.
BEGIN;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS horoscope TEXT;
COMMIT;

-- IMPORTANT: A pre-existing birthday column may still contain old dates.
-- Once existing profiles have been migrated/re-entered and all writers updated,
-- execute this separately to remove existing stored dates permanently:
-- ALTER TABLE public.users DROP COLUMN IF EXISTS birthday;
