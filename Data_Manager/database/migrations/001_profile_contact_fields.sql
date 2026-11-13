-- Run once in the PostgreSQL/Supabase SQL editor before using the updated app.
-- Existing profiles are preserved; missing optional values remain NULL.
BEGIN;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS race TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS insta_handle TEXT;
COMMIT;
