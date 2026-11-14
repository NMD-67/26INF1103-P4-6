# Database setup

The application uses direct PostgreSQL connections through psycopg, not the Supabase HTTP API.
For a new disposable development database, run Data_Manager/database/schema.sql using
psql or the Supabase SQL editor. It creates all nine tables, unique constraints needed by
ON CONFLICT, and foreign keys that remove profile lists, matches in both directions and
Telegram links when a user is deleted. Birthday is input-only and has no storage column.
OTPs have no user FK because verification happens before account creation; expired OTPs
are rejected and replaced on the next request.

The script deliberately fails if these tables already exist. Do not run it as an upgrade
on your shared database. For an existing database, use verify_constraints.sql and have the
database owner reconcile the schema through a reviewed migration. The earlier migration
files are incremental historical changes, not a complete initial setup.

Configure SUPABASE_URL in your local .env with the PostgreSQL connection string, including
credentials; never commit it. Keep the connection server-side and do not expose database
credentials to clients. No public HTTP access or grants are required by this application.

This schema has not been executed against a PostgreSQL server during this change.
Before submission, use disposable users to verify create/update/reload, all four scores
and reason, accept/reject, mutual connections and cascade deletion, then run the application
and offline suite in Docker. Do not claim the live database is migrated by adding this file.
