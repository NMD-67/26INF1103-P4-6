-- READ ONLY: run in the Supabase SQL editor. Does not change data or constraints.
-- Compare with the actual repository schema before preparing migrations.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users', 'matches', 'dealbreakers', 'hobbies', 'interests',
                     'ccas', 'events', 'otp', 'bot_users')
ORDER BY table_name, ordinal_position;

-- ON CONFLICT targets must match an actual unique/primary key.
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('users', 'matches', 'dealbreakers', 'hobbies', 'interests', 'ccas', 'events')
ORDER BY tablename, indexname;

-- Check child tables reference users; both match directions must be considered.
-- Missing rows mean no such FK exists. CASCADE removes dependent rows when deleting
-- a user; other actions require explicit handling. Verify using disposable users.
SELECT child.relname AS child_table, c.conname AS constraint_name,
       pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class child ON child.oid = c.conrelid
JOIN pg_namespace n ON n.oid = child.relnamespace
WHERE c.contype = 'f' AND c.confrelid = 'public.users'::regclass
  AND n.nspname = 'public'
ORDER BY child.relname, c.conname;
