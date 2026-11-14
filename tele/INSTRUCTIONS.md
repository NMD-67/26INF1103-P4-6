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
   Login displays the privacy notice before prompting for the ID. An ID supplied
   with `/login ID` is not processed; enter it again after the notice. `/otp CODE`
   works, and the old `/otp ID CODE` works only when
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

## Shared implementation

- IO_Manager/profile_form.py owns CLI/Telegram form and storage mapping.
- Logic_Manager/services/recommendation_service.py coordinates fresh recommendations.
- Logic_Manager/Matching/scoring_pipeline.py is the shared scoring/calculation/save implementation.
- Logic_Manager/Matching/score_calculator.py calculates the 40/30/30 weighted overall score.
- Logic_Manager/Matching/compatibility_classifier.py applies the multi-condition category rule.
- IO_Manager/telegram/ contains TelegramApp, TelegramProfileForm and TelegramIO.
- tele/bot.py wires the services and polling. Run it with python -m tele.bot.

Three AI category scores, overall score and reason are saved and displayed in both interfaces.
The same compatibility category is shown for recommendations and mutual connections.
The new database setup is documented in docs/database_setup.md.

Demonstrate real OTP, profile save/reload, edits, decisions and mutual contacts against a
development database. Offline tests never send messages, email or real AI requests.

## Review AI suggestions

Each successful connection result has Keep suggestions and Regenerate buttons.
Regenerate asks for 1-500 characters of feedback; 0 cancels. Avoid entering contact
or identifying information. The service rechecks mutual acceptance before requesting
new suggestions. Failed attempts preserve the last successful result and contacts.
Each connection review allows three submitted attempts, including failed requests.
Opening /connections again starts a new review; this is a per-review limit, not a
persistent API quota. Buttons are bound to the user and chat; old buttons expire
after regeneration, keep, logout, restart or refreshing connections.
Keep applies to the current session: suggestions/feedback are not saved to the database.
The offline suite includes both UserFeedbackTests and Telegram review tests.
