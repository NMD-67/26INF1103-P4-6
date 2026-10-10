# **SITogether**

**_1\. Problem Statement and Target Users_**

- **Problem Statement:** SIT students have **limited** opportunities to discover and meaningfully interact with new people beyond **face-to-face** encounters, making it **difficult** to form **new social and romantic relationships**.
- **Background:** Despite being part of a **large student community,** students may only interact with a **small** group of people through their **classes**, **clubs**, or **existing social circles**. As a result, many students may not have the opportunity to meet or get to know others across the **wider SIT community**.
- **Objective:** To create a programme that provides SIT students with more opportunities to discover, interact with, and get to know **new** people, with the aim of **encouraging meaningful social** and **romantic connections**.
- **Target Audience:** SIT Students

**_2\. User Inputs \- Link to Google Sheets_**  
**Background Information:**

- Name, Birthday (DD/MM/YYYY), Religion, MBTI → 16 Personalities
- Year, Course, Student ID

**Personal Information:**

- Sexual Orientation: Heterosexual/ Homosexual/ Bisexual
- Here For: Friends/ Relationship
- Expectations in Relationships

**Extracurriculars:**

- Current CCAs/ Events Joined (in SIT), Hobbies,Outside Interest Group

**_3\. Use of AI \- Claude_**

| AI Feature                                   | How AI is Utilized                                                                                                           | AI Output/Recommendation                                                                                                         |
| :------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| **Compatibility Matching**                   | AI will analyse user’s profiles, to identify similarities between two students.                                              | Generates a **_Compatibility Score_** and highlights key areas of similarity.                                                    |
| **Personalised Match Recommendations**       | AI analyses a user’s profile together with profiles they liked or skipped, to better understand their preferences over time. | Recommends students who are more likely to be compatible with a user and improves on future matchmaking suggestions.             |
| **Conversations & Date Suggestions**         | AI uses information from both matched user’s profiles and shared interests to generate personalised suggestions.             | Provides both users with: Conversation Starters Common-Interest Topics Possible Date Activities Relevant SIT Events              |
| **Content Safety & Moderation**              | AI analyses messages and profile content for potentially inappropriate behavior.                                             | Flags potentially harmful content for review and warns users where appropriate. Repeated or serious violations are escalated.    |
| **Profile Image Verification**               | AI analyses uploaded profile images for signs of manipulated, AI-generated or duplicated images.                             | Assigns a risk/verification result and flags suspicious images for further review rather than automatically banning the student. |
| **Match Feedback & Compatibility Analytics** | AI analyses feedback after matches, such as whether users continued chatting or mutually liked each other.                   | Identifies patterns associated with successful matches and uses them to improve future compatibility recommendations.            |

**_4\. Business Rules_**

| SIT Student Validation                        | Only verified SIT students may create an account. Users must register using their SIT student email / Student ID.                                                                                                                                                          |
| :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Account/Profile Eligibility**               | A user must have a **verified account and completed profile** before appearing in matchmaking recommendations.                                                                                                                                                             |
| **Compatibility Range**                       | Matches will be according to the AI-generated compatibility score: **85 \- 100%**: High Compatibility **70 \- 84%**: Shown after high compatibility users **Below 70%**: Low Compatibility; Lower Priority                                                                 |
| **Match Status**                              | **“Accept", “Reject”:** Social media handles will be revealed once a match is created.                                                                                                                                                                                     |
| **Flag System _(Human-In-The- Loop System)_** | AI will assign potentially inappropriate or suspicious content a **risk/confidence score**. Low-confidence cases will not automatically penalise users. Content that exceeds a defined threshold will be **flagged for human review** before disciplinary action is taken. |
| **Violation System**                          | Violations will be recorded against the user's account: **1st Violation:** In-App Warning **2nd Violation:** Email Warning **3rd Violation:** Escalate to Administrator                                                                                                    |
| **Match Recommendation Rule**                 | Users who have already **rejected, blocked, or reported each other** will not be recommended to one another again. Existing matches should also be excluded from new recommendations.                                                                                      |
| **Blocking & Reporting Rule**                 | When a user blocks another user, both users will be removed from each other's recommendations. Reports will be stored for administrator review.                                                                                                                            |

## Technical Documentation

### About

This program's main interface is using the command line, as it is the minimum requirement for the project. In addition to the command line, we are also planning to add a Telegram Bot/Web Interface. Therefore, the structure of our program will be planned with these extensions in mind.

#### Program Structure

```
project/
|---src/
|   |---auth.py           //Handles user CRUD (Create, Read, Update, Delete)
|   |---ai_manager.py     //Handles API calls to AI systems
|   |---logic_manager.py  //Handles user matching based on AI results
|   |---email.py          //Email service for auth
|---cli/
|   |---main.py           //The file to run the app via CLI
|---tele/
|   |---bot.py            //The logic behind the tele bot
|---api/
|   |---server.py         //The server used for web interface
|---database/
|   |---db.py             //Handles the connection to the database
```

#### User fields

```py
{
  student_id: int,
  name: str,
  birthday: int/datetime,
  gender: str,
  year: int,
  course: str,
  bio: str,               #Optional
  religion: str,          #Optional
  MBTI: str,              #Optional
  sexual_orientation: str,
  here_for: str,          #Friends/Relationship
  expectation: str,       #Short/Long term etc.
  cca: [str],             #Optional
  sit_events: [str],      #Optional
  hobbies: [str],
  interest_groups: [str], #Optional
  insta_handle: str,      #Optional
  tele_handle: str        #Optional
}
```

##### How to add user as JSON

Go to `/database/db` and scroll to the bottom. There is an example of how it can be done. Simply replace the `student_json` object with the one you wanna import.

#### auth.py

This file contans all the functions and modules for user handling. Note that as the functions require updating of the database, all the functions are asynchronious. The functions are as such:
| Function | Parameters | Return | Remarks |
|---|---|---|---|
|Login | student_id `int` | status `int` | Returns a [http status](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) depending on the progress of the login |
|GetUserInfo | student_id `int` | Dict {<br>success: `bool`,<br> user: `dict`,<br> status: `int`, error: `str`<br>} | Return value will on have an error value if an error occured. |
|UpdateUserInfo | student_id `int` | status `int` | Returns a [http status](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) depending on the progress of the update |
|DeleteUser | student_id `int`| status `int` | Returns a [http status](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) depending on the progress of the deletion |

## Profile CLI and Google Sheets sync

Run from the repository root:

```powershell
py -m pip install -r requirements.txt
py main.py
```

Profiles are stored only in the `users` tab of the SITogether spreadsheet.
Place the Google service account credentials at `database/service_account.json`
locally; never commit credentials. This credential file is still required and is
not a profile database. The service account needs edit access to the sheet.

Saving matches the exact `student_id` column and refuses duplicate IDs. It
updates only form fields, preserving unrelated columns.
Lists display as comma-separated text, with empty lists shown as blank cells.
MBTI personality names and completeness are calculated when needed, not stored separately.
There is no offline profile save or automatic retry. A connection failure is
reported to the user; a failed request may require checking Sheets and retrying.

The September 2026 header migration keeps `bio`, renames `expectation` to
`expectations`, `cca` to `ccas`, `sit_event` to `events`, and `tele_handle` to
`telegram_handle`. `sexual_orientation` is replaced by `match_preference`;
existing users must re-enter Male, Female, or Both. Original profiles are in
`users_backup_20260928_before_headers`. Keep other running bot copies aligned
with these new headers.

Run the offline sync regression checks without credentials or live API calls:

```powershell
py tests/test_profile_sync.py
```

These checks supplement, but do not replace, the assignment's AI business-rule tests.

## Telegram profile setup

Start the bot from the repository root (with dependencies installed):

```powershell
py -m tele.bot
```

The existing `.env` supplies `TELE_API_KEY` and `EMAIL_PASSWORD` for the bot
and email login. The existing service-account file is required for Sheets.
Run only one polling instance of this bot token; coordinate with the team
before replacing an already-running instance.

In a private Telegram chat:

1. `/login <student_id>` and then `/otp <student_id> <otp>` verify the account.
2. `/setup` collects the same profile fields as the CLI, using the verified ID.
3. Reply with text or option numbers; `/skip` skips optional questions only.
4. Review the summary and send `/save` to save to the `users` row in Sheets.
5. `/profile` displays the saved sheet profile. Its setup button restarts the full form.

`/cancel` discards an unsaved draft; `/setup` starts it again. Nothing is
written until `/save`. If saving to Sheets fails, the draft stays in the running
bot and `/save` can retry. Drafts exist only in memory and are lost on bot restart. Existing
single-field editing remains available; finish or cancel setup before using it.

Offline Telegram tests (no real email, Telegram messages or Sheets writes):

```powershell
py tests/test_telegram_setup.py
py tests/test_profile_sync.py
```

The Dockerfile includes the shared profile modules used by the bot. The live
Telegram/OTP flow and Docker build still require verification in the team's
runtime; offline tests do not contact these external services.

### Shared profile saving

`database.db.save_profile()` is the common saving entry point for terminal
setup, Telegram setup, and individual edits. All profile storage functions
and the Google Sheets connection now live in `database/db.py`. `partial=True` updates only the edited
fields; the default saves the complete profile. The result contains `saved`
and `message`. A failed save keeps the Telegram draft/edit active for retry.
No local profile file is read, written, or recreated.

`database.db.get_profile()` reads a profile from Sheets and converts list
cells into Python lists. It looks up the MBTI personality name in memory. `database/db.py` also
keeps the existing OTP and Telegram-account-link operations. It connects on
first use, using `SITOGETHER_SPREADSHEET_ID` or the project default.

### Reading the profile code

Start with `profile_schema.py` for questions and `main.py` for the terminal flow.
The Telegram code uses `tele/bot.py` for commands and editing, and
`tele/profile_setup.py` for setup and shared question/button functions.
Courses use typed numbered answers. Each user's `context.user_data` holds the
current draft or edit in memory. Session tokens reject old buttons.

Run all offline checks with:

```powershell
py tests/test_profile_sync.py
py tests/test_shared_saving.py
py tests/test_telegram_setup.py
py tests/test_telegram_menus.py
py tests/test_telegram_edits.py
```

This Sheets-only design does not implement the assignment's local CSV/JSON
storage requirement. The team needs to resolve that requirement for submission.

### Storage backend boundary

The CLI and Telegram profile flows call `database.db.get_profile(student_id)`
and `database.db.save_profile(profile, partial=False)`. Login continues to use
the existing user, OTP, and Telegram-link functions in the same module.

To replace Sheets with MongoDB, replace the storage implementation in `db.py`
and keep these public function signatures, returned dictionary keys/status
codes, and field types compatible. Full setup creates or updates a profile;
partial edits update only supplied fields and must not create missing users.
The CLI and Telegram callers should then need no storage-specific changes.
MongoDB still requires its driver in `requirements.txt`, connection settings,
database setup and any data migration. This project still uses Sheets today.

`data_manager.py` has been removed by project decision. Along with local file
storage removal, this departs from the assignment's stated module requirements.

Instagram is an optional setup field stored in the existing `insta_handle` column.
Users can enter their username with or without @, skip it during setup, and edit
it through /profile. It appears as Instagram Handle in profile summaries.
