# SITogether

SITogether helps Singapore Institute of Technology students discover friendships
and relationships beyond their existing classes and social circles. It is an
INF1103 Phase 2 object-oriented project with a terminal application and Telegram
bot sharing the same profile, recommendation and connection services.

The active application uses **PostgreSQL**, **Groq** and a local embedding model.
It no longer uses Google Sheets or local JSON files for profile storage.

## Implemented features

- School email OTP login using a seven-digit student ID.
- Profile creation, viewing, validated editing and account deletion.
- Configurable age limits and mutual preference/dealbreaker filtering before AI scoring.
- Three AI compatibility scores and a short explanation for each scored pair.
- Independent interest, MBTI and relationship-goal checks that review AI scores.
- Weighted overall scores, multi-condition compatibility labels and ranked recommendations.
- Accept/reject decisions and connections after both students accept.
- Contact handles and personalised conversation/activity suggestions for mutual connections.
- Feedback-based suggestion regeneration in both CLI and Telegram, with up to three
  regeneration attempts per review session. Failed regeneration retains previous suggestions.
- Shared privacy notice, bio guidance, error logging and offline regression tests.

Image verification, blocking/reporting, automatic moderation and learning from past
accept/reject decisions are not implemented features. Excluding previously decided
candidates is a filter, not a trained recommendation model.

## Quick start with Docker

Run commands from the repository root. Install and start Docker Desktop with Linux
containers enabled. You also need a configured PostgreSQL database, OTP sender
credentials and Groq keys; Telegram additionally needs a bot token.

1. Set up the database as described below.
2. Create a local `.env` using the configuration example below.
3. Build the shared image:

```powershell
docker build -t sitogether .
```

4. Run the terminal application:

```powershell
docker run --rm -it --env-file .env sitogether
```

Or run the Telegram bot using the same image:

```powershell
docker run --rm --env-file .env sitogether python -m tele.bot
```

The Dockerfile defaults to `python main.py`; overriding the command starts the bot
or tests. There is one Dockerfile for all three uses. No ports need publishing for
terminal use or Telegram polling. Run only one polling process per bot token.

The build downloads CPU PyTorch, sentence-transformers and the embedding model.
It needs internet access and produces a larger image than the earlier application.
The model is stored at `/app/embedding-model` and needs no network during review.
Normal application use still needs access to PostgreSQL, Groq, email and, for the
bot, Telegram. Credentials are supplied at runtime rather than baked into the image.

## Configuration

Create `.env` in the repository root. The following values are placeholders, not
working credentials. There is currently no committed `.env.example` file.

```dotenv
SUPABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
EMAIL_PASSWORD=YOUR_CONFIGURED_SENDER_APP_PASSWORD
PROFILE_MATCHING_API_KEY=YOUR_GROQ_SCORING_KEY
MATCHMAKING_API_KEY=YOUR_GROQ_SUGGESTION_KEY
RAPH_AI_KEY=YOUR_OPTIONAL_BACKUP_SUGGESTION_KEY
TELE_API_KEY=YOUR_TELEGRAM_BOT_TOKEN
```

| Setting | Purpose |
| --- | --- |
| `SUPABASE_URL` | PostgreSQL connection URI, including database credentials. Despite its name, this is not the Supabase HTTPS API URL. SSL is required by the connection class. |
| `EMAIL_PASSWORD` | SMTP credential for the sender configured in `IO_Manager/email_sender.py`. The default sender is the team's Gmail address; changing only the password does not change the sender. |
| `PROFILE_MATCHING_API_KEY` | Groq compatibility-scoring key. `GROQ_API_KEY` is a fallback variable name. |
| `GROQ_KEY_NAMES` | Optional comma-separated environment variable names for multiple scoring keys, tried in order. Overrides the default scoring-key lookup. |
| `MATCHMAKING_API_KEY` | Primary Groq key for connection suggestions. |
| `RAPH_AI_KEY` | Optional backup Groq key for connection suggestions. Omit if unused. |
| `TELE_API_KEY` | Telegram bot token; required only for the bot. |
| `LOCAL_EMBEDDING_MODEL` | Optional local model directory for direct Python execution. Docker configures its own packaged directory. |

For example, multiple scoring keys can be configured as:

```dotenv
GROQ_KEY_NAMES=PROFILE_MATCHING_API_KEY,SCORING_BACKUP_KEY
PROFILE_MATCHING_API_KEY=YOUR_FIRST_KEY
SCORING_BACKUP_KEY=YOUR_SECOND_KEY
```

Do not commit `.env`, connection passwords, API keys, email credentials or database
exports containing personal data. Environment variables already set in your shell
can take precedence over values loaded from `.env`.

Missing scoring credentials disable Find matches rather than blocking startup.
Unavailable suggestion credentials should not hide existing connection contacts.
Database and email access are still required for normal login.

## Database setup

The repositories use direct PostgreSQL connections through psycopg. Supabase can
host the database, but the application's active storage path does not use its HTTP SDK.

- **New empty development database:** run
  [`Data_Manager/database/schema.sql`](Data_Manager/database/schema.sql) using a SQL
  client or the Supabase SQL editor. It creates tables, constraints and relationships.
- **Existing shared database:** do not rerun the complete schema as an upgrade.
  Review [`verify_constraints.sql`](Data_Manager/database/verify_constraints.sql)
  and coordinate any migration with the database owner.
- Existing databases need the current profile/contact and score columns. For birthday
  restoration, see [`003_restore_birthday.sql`](Data_Manager/database/migrations/003_restore_birthday.sql).
  Verify an existing birthday column has type `DATE`; the migration does not convert it.
- Migration files represent historical changes. In particular, migration 002 removed
  birthday storage and migration 003 restores it. Do not execute historical scripts
  blindly against a populated database.

See [database setup notes](docs/database_setup.md). Adding schema files to Git does
not apply them to the live database. Check create/update/reload, matching decisions,
mutual connections and deletion using disposable development accounts.

## Run directly with Python

Python 3.12 is the Docker baseline. Use an isolated environment from the repository root:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

For full local interest review, download the model once to a directory outside the
repository. Run this in a fresh process, before importing the application:

```powershell
$env:LOCAL_EMBEDDING_MODEL = Join-Path $env:LOCALAPPDATA 'SITogether\embedding-model'
.\venv\Scripts\python.exe -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save(os.environ['LOCAL_EMBEDDING_MODEL'])"
```

Set `LOCAL_EMBEDDING_MODEL` to the same path in future sessions or in your local
`.env`. Do not carry a Windows model path into the Linux container; Docker uses
`/app/embedding-model`.

```powershell
.\venv\Scripts\python.exe main.py
# Or:
.\venv\Scripts\python.exe -m tele.bot
```

Without the local model, the existing fallback logs a warning and retains the
MBTI/goals checks, but skips semantic interest review. Full hybrid review requires
the model. A manual live-service runner is not needed to launch either application.

## Using the application

### Terminal

Read the privacy notice, enter your student ID and verify the OTP sent to
`<student_id>@sit.singaporetech.edu.sg`. New users complete and confirm their profile.
The main menu provides:

1. Find matches: browse ranked profiles and accept, reject or return.
2. View connections: see mutually accepted users, contact handles and suggestions.
3. My profile: display saved details.
4. Update profile: edit fields, review changes and confirm saving.
5. Delete account: confirm account removal.
6. Quit: leave the application.

Unsaved profile drafts are held in memory. Failed edits retain the draft for retry
within the running session; drafts do not survive restarting the application.

### Telegram

Open a private chat with the configured bot, then:

1. Send `/start` or `/login`, read the notice and reply with your student ID.
2. Reply with your OTP or send `/otp <code>`.
3. Complete `/setup` if required, then use `/menu` or Telegram's command menu.

| Command | Action |
| --- | --- |
| `/profile`, `/update` | View or edit your profile. |
| `/matches` | Browse recommendations and accept/reject using buttons. |
| `/connections` | View mutual contacts and suggestions; use Keep/Regenerate for feedback. |
| `/setup`, `/save` | Collect profile answers and review/save the draft. |
| `/skip` | Skip an optional question. |
| `/cancel` | Cancel the current action. |
| `/delete_account` | Start confirmed account deletion. |
| `/logout` | End the Telegram account session. |
| `/help`, `/menu` | Show help or available actions. |

Choice questions use buttons; course selection uses a typed numbered answer.
The CLI and bot use shared services, while their input and display adapters differ.

## Matching and AI workflow

```text
Profile and preferences
    -> mutual eligibility filtering; exclude self and previous decisions
    -> Groq generates three scores and a reason
    -> validate response structure and score ranges
    -> independent hybrid review of category scores
    -> calculate weighted overall and rank
    -> save scores and reason in PostgreSQL
    -> display recommendations and record accept/reject
    -> mutual connection: reveal contacts and generate suggestions
```

The configured scoring model defaults to `openai/gpt-oss-20b`; suggestions use
`openai/gpt-oss-120b`. These are code defaults, not a guarantee of provider availability.

### Scores and review

The three categories are interests/lifestyle, personality/values and relationship
goals. Review uses local semantic interest similarity, an MBTI similarity table and
deterministic goal rules. A category outside the review tolerance is brought within
25 points of its independent check. Invalid reviewer values/counts are logged and
previous valid scores are retained. Dry-run review logs changes without applying them.
The original AI reason is preserved; review does not regenerate its wording.

The overall score is calculated in Logic Manager, not by the AI:

```text
overall = round(0.40 * interests + 0.30 * personality + 0.30 * goals)
```

The multi-condition label uses all three stored category scores:

- Strong compatibility: all three are at least 70.
- Moderate compatibility: all three are at least 50, but the strong rule is not met.
- Low compatibility: other valid combinations.
- Not available: any category is missing or invalid.

Scores and labels are project heuristics, not scientifically established probabilities.
Both recommendations and connections display the scores, overall, label and reason.
See [business-rule notes](docs/ai_business_rule.md).

### Candidate count and API usage

The normal CLI/Telegram `RecommendationService` currently scores **all eligible
candidates** passed to it. Reopening Find matches can score pending candidates again;
there is no claim of full scoring-cache reuse.

The separate `MatchService.get_next_candidate()` route reuses eligible pending
recommendations and generates up to **five candidates per batch** when needed.
That means the first five eligible candidates before scoring, not the global top
five after comparing everyone. It is not a permanent five-row database limit.
Both paths now delegate scoring/review/calculation/saving to `ScoringPipeline`.

## Code structure and responsibilities

| Location | Responsibility |
| --- | --- |
| `main.py`, `sitogether_app.py` | CLI startup, service wiring and menu orchestration. |
| `tele/bot.py` | Telegram startup and polling lifecycle. |
| `IO_Manager/` | Console/Telegram input and display, profile forms/validation, email delivery adapter. |
| `AI_Manager/` | Prompt construction, API clients, structured response parsing, suggestions and independent review components. |
| `Logic_Manager/` | Profile rules, filtering, weighted scores, classification and application services. |
| `Data_Manager/` | PostgreSQL pool, repositories, schema/migrations and user-source adapter. |
| `models/` | User/Profile/Candidate/Match/DealBreaker and category-score value objects. |
| `config/` | Shared field questions/options/storage metadata and privacy text. |
| `results/`, `exceptions/` | Shared operation results and error types. |
| `ci/`, `tests/` | Maintained offline checks and supporting test documentation. |
| `.github/workflows/ci.yml` | Docker build, offline regression suite and packaged-model smoke check. |

To change profile questions, start at `config/user_fields.py`. `PROFILE_FIELDS` is
generated from the configuration rather than maintained as a separate schema file.
The form captures identity/background, preferences, contact handles and interests.
Dealbreakers are a nested model/storage structure, not a standalone input question.
Race/religion dealbreaker lists are exclusion lists; they are distinct from the
student's own race/religion fields.

### OOP and SOL design evidence

- Classes/encapsulation: application, services and repositories own state and expose
  operations; internal collaborators commonly use `_` names by convention.
- Abstraction/interfaces/inheritance: `CompatibilityScorer` and `UserSource` define
  contracts; concrete scorers and the repository source implement them. Profile,
  Candidate and Match extend the user model hierarchy.
- Polymorphism/LSP: scoring clients use the same scorer contract for live, lazy and
  fake scorers. Offline tests exercise substitutions without real API calls.
- Association: services collaborate with separately supplied repositories/scorers.
- Aggregation: the application receives services with independent lifetimes.
- Composition: the key pool constructs and closes its owned Groq clients.
- SRP: input adapters, AI calls, business calculations and persistence have separate
  responsibilities. The shared pipeline coordinates rather than duplicating them.
- OCP: new scorer or category-validator implementations can follow existing contracts
  without rewriting the consumers' scoring loop.

These examples support, but do not replace, the report's UML diagrams and explicit
SRP/OCP/LSP explanations. Small startup/factory functions remain; the application
behaviour is organised around collaborating objects.

## Privacy and failure handling

A privacy notice appears before collecting the student ID. Full birthday is currently
stored as a PostgreSQL `DATE` and used to calculate age/horoscope. Dedicated name,
student ID, birthday and contact fields are excluded from AI prompts. Free-text bio
or expectations may still contain identifying information, so users are told not to
enter it. Contact handles are displayed for mutual connections.

Optional fields can be skipped; users can update or delete their account. Database
foreign-key behaviour must match the supplied schema for complete related-row
cleanup. A privacy notice alone is not a claim of full PDPA compliance.

Failures are logged and surfaced through controlled results/menu messages. Examples
include unavailable scoring keys, invalid AI responses, failed saves and unavailable
suggestions. Live login still fails if database/email is unreachable. Failed suggestion
generation preserves existing contact details. Do not publish logs containing personal data.

## Tests and Continuous Integration

Run the maintained offline suite without credentials or live services:

```powershell
python -B ci/offline_tests.py
```

Or use the same image as the application:

```powershell
docker run --rm --network none sitogether python ci/offline_tests.py
```

The suite covers profile validation/privacy, OTP handling, preference filtering,
AI response parsing, key fallback, multi-condition rules, reviewer corrections and
malformed outputs, ranking/saving, failure recovery and CLI/Telegram behaviour.
Unit tests use fake external services and block network access; the heavy embedding
model is mocked there. CI separately loads and runs the actual packaged embedding
model with networking disabled.

GitHub Actions runs on pushes, pull requests and manual dispatch. It builds Docker,
runs offline tests and checks the packaged model. Check **Actions -> SITogether CI**
for the result; a local test pass is not proof of a successful Docker build or CI run.

Verification at this README update: **106 offline tests passed**. The latest Docker
build/model check was not verified locally because Docker engine access was denied.
Live PostgreSQL, email, Groq and Telegram checks are separate from offline tests.
See [hybrid review notes](ci/HYBRID_REVIEW.md).

## Team workflow and submission checks

1. Fetch/pull the latest shared branch before starting work.
2. Create a focused branch, for example `fix/profile-validation` or `feat/match-feedback`.
3. Make a small change, run relevant checks and review the diff for secrets.
4. Commit with a descriptive name, for example `fix: preserve profile draft after save failure`.
5. Push the branch, open a pull request, obtain team review and check CI before merging.

Before submission, verify the final committed image and both interfaces against a
development database. Include the engineering report/UML, SOL explanations, exception
matrix, new-feature explanation/tests, TeamAI-d records and the required repository/
commit/CI evidence. Database CRUD supplies the project's additional advanced feature.

The multi-condition rule above is implemented, but preservation of the original
Phase 1 rule still needs comparison with that submission or documented lecturer
approval for a replacement. This README does not certify every rubric item or a grade.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Database pool timeout | PostgreSQL URI, project availability, credentials, SSL and network access. A successful TCP port test alone does not prove database login works. |
| OTP does not arrive | Configured sender credential, email delivery logs and school inbox. Never print the correct OTP to diagnose login. |
| Groq authentication/model error | Correct key variable, key validity and configured model availability. |
| Interest model unavailable | Build the updated image or configure a downloaded local model directory. MBTI/goals-only fallback is not full review. |
| Telegram is silent/conflicting | Correct bot/token, running process and only one polling instance for that token. |
| Missing column/ON CONFLICT error | Code/schema mismatch; review schema and constraints rather than removing validation. |
| Docker engine connection error | Start Docker Desktop and ensure the Linux engine is accessible. |

