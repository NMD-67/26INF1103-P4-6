# SITogether CI

The workflow in `.github/workflows/ci.yml` builds `Dockerfile.main` and runs
`ci/offline_tests.py` on pushes, pull requests and manual runs.
Failed builds or tests fail the job. No secrets are required.

## Run the same check locally

From the repository root, with Docker Desktop running:

```powershell
docker build --file Dockerfile.main --tag sitogether-ci .
docker run --rm --network none sitogether-ci python ci/offline_tests.py
```

Building needs internet access to download dependencies. Tests run without
network access. Do not supply `.env` or credentials to the test container.

Without Docker, after installing requirements:

```powershell
python ci/offline_tests.py
```

Tests use real application classes and fake external services. They check
validation, dealbreaker rules, AI responses, OTP handling, scoring key fallback,
profile-save recovery, repository outcomes, connections and startup wiring.
They do not verify live email delivery, live AI availability, real database
constraints or Telegram. Check those separately. The two old automated_test_script.py
commands now forward to this maintained suite.

## Publish and verify

Commit the workflow, `ci` directory and updated `Dockerfile.main`, then push.
Open GitHub's Actions tab and select **SITogether CI**. Check both the build and
test steps. Record the successful run URL and commit in the engineering report.
Do not describe CI as passing until the GitHub run finishes successfully.

This workflow does not deploy the application or automatically merge changes.

## Remaining quality fixes

The suite also runs `ci/quality_tests.py` and the focused mutual-preference
checks in `tests/test_mutual_preference_filter.py`. Dockerfile.main copies both.
Only these maintained tests are loaded: other old test scripts may contact live
services and are not discovered automatically.

The new checks cover the secondary matching route's exclusions, stale stored
profiles, email timeout/failure handling, database pool cleanup, failed account
creation, missing suggestion credentials, exhausted scoring keys, and real
service/repository decision and deletion return values using a fake connection.
They do NOT establish that SQL executes correctly against the production schema.

Both of these old commands now run the same suite:

```powershell
python automated_test_script.py
python tests/automated_test_script.py
```

## Configuration and live verification

Copy `.env.example` to `.env` and fill in your own values locally. Never commit
credentials. The active CLI uses PostgreSQL through psycopg; SUPABASE_URL must
be a PostgreSQL connection URI, not the Supabase HTTPS API URL.

The email sender and database setup now use EmailSender and DatabaseConnection.
The old send_email/create_connection_pool functions are compatibility wrappers
for existing imports, not duplicate implementations. Older spreadsheet modules
remain outside the main CLI path and are not claimed to be fully migrated.

Missing suggestion keys now disable suggestions gracefully while preserving
mutual contacts. Login still needs working database/email credentials; matching
still needs a valid scoring key. A network outage can still prevent login.

The three-score AI integration is deliberately deferred. A passing offline suite
is NOT proof that Find Matches can save the newly extended score result. Add a
real scorer-result/service/repository contract test when that interface is ready.

Before submission:
- Complete the teammate's score integration and its integration tests.
- Export a schema-only migration from the actual database (no profile rows or
  credentials). Review it and verify setup in an empty development database.
- Use `Data_Manager/database/verify_constraints.sql` to inspect the live schema.
  Verify uniqueness for ON CONFLICT targets and deletion rules for dependent data.
- On a development database, create, update, reload and delete disposable users;
  confirm one-sided acceptance hides contacts and mutual acceptance reveals them.
- Build Dockerfile.main and test the real login/profile/connection flows.
- Push the branch, obtain review, and record the successful latest CI run URL.
- Update UML for EmailSender, DatabaseConnection and RepositoryUserSource; include
  the exception matrix, new feature evidence, SOLID explanation and Team AI-d log
  in the report. Do not describe these documents as verified by the test suite.
