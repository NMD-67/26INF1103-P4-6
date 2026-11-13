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
constraints, Telegram or the old test scripts. Check those separately.

## Publish and verify

Commit the workflow, `ci` directory and updated `Dockerfile.main`, then push.
Open GitHub's Actions tab and select **SITogether CI**. Check both the build and
test steps. Record the successful run URL and commit in the engineering report.
Do not describe CI as passing until the GitHub run finishes successfully.

This workflow does not deploy the application or automatically merge changes.
