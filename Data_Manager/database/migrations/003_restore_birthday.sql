-- Adds birthday storage without changing existing profile data.
-- Run before deploying code that reads/writes birthday.
BEGIN;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS birthday DATE;
COMMIT;
-- If birthday already exists, verify its type is DATE using verify_constraints.sql.
-- This script does not convert an existing TEXT column or recover deleted birthdates.
