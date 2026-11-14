# Telegram version of SITogether

## Run locally

Install requirements into the same Python environment used to run the project.
Configure the local `.env` using `.env.example`. Required for login:
TELE_API_KEY, PostgreSQL SUPABASE_URL, and EMAIL_PASSWORD. Scoring uses
PROFILE_MATCHING_API_KEY (or GROQ_API_KEY / GROQ_KEY_NAMES); suggestion generation
uses MATCHMAKING_API_KEY and optional RAPH_AI_KEY. Never commit the real values.

From the repository root:

```powershell
python -m tele.bot
```

Only run one polling instance for this bot token. Quit any older terminal/container
before starting another instance. The bot creates no database connection merely
by being imported. Startup creates the pool; exit closes the pool and AI clients.
Database tables include the existing bot_users(tele_id, student_id) mapping; its
tele_id must have a unique constraint for login linking. The database owner must
verify foreign keys/cascades separately.

## Docker

One Dockerfile builds both interfaces. Its default command runs the CLI; override
the command to run Telegram.

```powershell
docker build -t sitogether .
docker run --rm --env-file .env sitogether python -m tele.bot
```

Alternatively use `docker compose up --build`. Compose now uses PostgreSQL and
no longer mounts Google Sheets service_account.json. Do not run Compose and the
terminal bot simultaneously with the same token.

Offline checks (no credentials, no external calls):

```powershell
python ci/offline_tests.py
docker run --rm --network none sitogether python ci/offline_tests.py
```

## User workflow

1. Send /start then /login, enter your 7-digit student ID, and enter the email OTP.
   `/login ID` and `/otp CODE` also work. The old `/otp ID CODE` works only when
   the ID matches the pending login. Three incorrect attempts require a new login.
2. Complete the profile if prompted. Choose buttons for choices/MBTI; type a
   course number and free text. For blacklist fields, select all desired values
   then Done. /skip skips optional fields. Birthday is converted to age and
   horoscope before saving; the date itself is not written by this adapter.
3. Review the summary and confirm Save (or /save). Discard uses /cancel or the
   Discard button. Failed saves retain the draft while this bot process runs.
4. /menu shows Find matches, View connections, My profile, Update profile,
   Delete account and Quit / log out. /profile displays the same sections as CLI.
5. /update opens editable fields. Updates are drafts with validation and save
   confirmation; selecting Friends clears relationship expectations.
6. /matches displays a recommended profile with Accept/Reject. A successful
   decision advances automatically; Return to menu stops browsing. Old buttons
   cannot repeat a decision. Current eligibility is checked again before saving.
7. /connections displays all mutual contacts and AI suggestions. Contacts remain
   visible if suggestions fail; one-sided acceptance does not reveal contacts.
8. /delete_account asks for confirmation. /logout or /quit clears Telegram login
   and the in-memory draft without deleting your account.

Old aliases /find_match and /view_matches map to /matches and /connections.
Drafts and callback buttons are tied to the user and chat. Restarting the bot
loses drafts and browsing state; saved profiles and Telegram login links remain.

## Shared code / teammate handoff

- services/profile_form.py owns CLI/Telegram form and storage mapping.
- services/recommendation_service.py owns the existing CLI filtering/scoring/save
  sequence used by both interfaces.
- tele/telegram_app.py owns Telegram commands and login/browsing sessions.
- tele/profile_setup.py contains TelegramProfileForm, the draft/question workflow.
- tele/telegram_io.py reuses ConsoleIO's profile/candidate/connection formatting.
- tele/bot.py wires services and polling; there is no old spreadsheet setup path.

IMPORTANT: The previously deferred three-score integration is NOT implemented.
The old score.score / score.reason save call has moved from SITogetherApp into
RecommendationService.get_recommendations(). Coordinate that call with the new
ScoreResult, MatchService.create_match and repository signature. Until the
teammate's contract change is completed, generating/saving new recommendations
can still fail in BOTH interfaces. Passing mocked Telegram tests is not proof
that this pending integration works against the live database.

After that integration, demonstrate real OTP, create/save/reload, profile edits,
match decisions and mutual contacts in Telegram against a development database.
The current offline tests never send Telegram messages or email.
