import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from database import db
from src import matches
from src import auth
from Matching import matching_logic
from profile_schema import PROFILE_FIELDS

import io_manager
import logic_manager
import profile_matching_AI
import matchmaking_ai


def main():
    print("Welcome to SITogether")

    # 1. Send the OTP.
    while True:
        student_id = input("Enter your student ID: ").strip()

        if auth.is_valid_student_id(student_id):
            break

        print("Please enter a valid 7-digit student ID.")

    result = asyncio.run(auth.login_user(student_id))

    if result != 200:
        print("Could not send the OTP.")
        return

    print("Check your school email for the OTP.")

    # 2. Verify the OTP before accessing profiles.
    verified = False

    for attempt in range(3):
        otp = input("Enter your OTP: ").strip()
        result = auth.validate_otp(student_id, otp)

        if result in (200, 201):
            verified = True
            break

        if result != 403:
            print("Could not verify the OTP. Please try again later.")
            return

        print("Incorrect OTP.")

    if not verified:
        print("Too many attempts. Please restart the program.")
        return

    print("Login successful.")

    # 3. Complete the profile if needed.
    profile = db.get_profile(student_id)

    if not profile or not profile.get("profile_complete"):
        print("\nPlease complete your profile.")

        profile = io_manager.collect_profile(
            PROFILE_FIELDS,
            {"student_id": student_id},
        )

        io_manager.show_profile_summary(profile, PROFILE_FIELDS)

        if not io_manager.confirm("Save this profile?"):
            return

        result = db.save_profile(profile)

        if not result["saved"]:
            print(result["message"])
            return

        profile = db.get_profile(student_id)

        if not profile or not profile.get("profile_complete"):
            print("Please complete your profile before finding matches.")
            return

    while True:
        print("\n--- SITogether Menu ---")
        print("1. Find matches")
        print("2. View connections")
        print("3. My profile")
        print("4. Update profile")
        print("5. Delete account")
        print("6. Quit")
        choice = input("Choose an option: ").strip()

        try:

            if choice == "1":
                print("Finding compatible profiles. Please wait...")

                recommendations = []
                client = None

                try:
                    client = profile_matching_AI.get_groq_client()
                    recommendations = profile_matching_AI.AI_Profile_Matching(
                        student_id, client
                    )
                except Exception as error:
                    print("Could not generate new recommendations:", error)
                finally:
                    if client is not None:
                        client.close()

                if recommendations:
                    result = profile_matching_AI.Add_To_Database(
                        student_id, recommendations
                    )

                    if result != 200:
                        print("Could not save new recommendations.")
                        print("Checking previously saved recommendations instead.")
                else:
                    print("No new recommendations. Checking saved recommendations.")

                # Continue to browse saved recommendations.
                # Load saved recommendations.
                
                new_connections = []

                while True:
                    next_user = matching_logic.get_next_user(student_id)

                    if not next_user["success"]:
                        print(next_user["error"])
                        break

                    target_id = next_user["student_id"]
                    score = next_user["compatability"]

                    matched_profile = db.get_profile(target_id)

                    if matched_profile is None:
                        removed = matches.remove_recco_student_id(
                            student_id, [target_id]
                        )

                        if not removed["success"]:
                            print("Could not remove an unavailable profile.")
                            break

                        continue
                    print("\n--- Recommended Profile ---")

                    label = matching_logic.compatibility_label(score)
                    print(f"Compatibility: ({label})")

                    # Contact handles are shown only after mutual acceptance.
                    for field in [
                        "name", "year", "course", "bio", "here_for", "hobbies"
                    ]:
                        label = io_manager.profile_label(field)
                        value = io_manager.profile_value(
                            field, matched_profile.get(field)
                        )
                        print(f"{label}: {value}")

                    while True:
                        decision = input(
                            "\nEnter accept, reject, or 0 to return to go back to menu: "
                        ).strip().lower()

                        if decision == "0":
                            break

                        if matching_logic.check_user_decision(decision):
                            break

                        print("Please enter accept, reject, or 0 to go back to menu.")

                    if decision == "0":
                        break

                    outcome = matching_logic.handle_match_decision(
                        student_id, target_id, decision
                    )

                    if not outcome["success"]:
                        print(
                            outcome.get("error")
                            or "Could not save your decision."
                        )
                        break

                    if outcome["status"] == "matched":
                        print("You both accepted! You are now connected.")
                        new_connections.append(target_id)

                    elif outcome["status"] == "waiting":
                        print("Accepted. Waiting for the other student.")

                    elif outcome["status"] == "rejected":
                        print("Profile rejected.")
                for target_id in new_connections:
                    if not matching_logic.is_mutual_match(student_id, target_id):
                        continue
                    yours = db.get_profile(student_id)
                    theirs = db.get_profile(target_id)
                    if not yours or not theirs:
                        print("A matched profile could not be loaded.")
                        continue
                    print("Preparing suggestions for your new connection...")
                    result = matchmaking_ai.prepare_connection(yours, theirs)
                    print(matchmaking_ai.format_recommendations(result))

            elif choice == "2":
                print("Loading mutual connections and suggestions...")
                connections = asyncio.run(
                    matchmaking_ai.get_matches_for_user_async(student_id)
                )
                if not connections:
                    print("No mutual matches yet. Both students must accept each other.")
                for connection in connections:
                    print(matchmaking_ai.format_recommendations(connection))
                    print("================================================\n")

            elif choice == "3":
                profile = db.get_profile(student_id)

                if profile is None:
                    print("Your profile could not be found.")
                else:
                    print("\n--- My Profile ---")
                    io_manager.show_profile_summary(
                        profile, PROFILE_FIELDS
                    )


            elif choice == "4":
                profile = db.get_profile(student_id)
                if profile is None:
                    print("Your account could not be found. Please log in again.")
                    return

                fields = [f for f in PROFILE_FIELDS if f["key"] != "student_id"]
                changed = False

                while True:
                    print("\n--- Update Profile ---")
                    for n, f in enumerate(fields, start=1):
                        print(f"{n}. {io_manager.profile_label(f['key'])}")

                    number = input("Choose a field to update (0 to finish): ").strip()

                    if number == "0":
                        break

                    if not number.isdigit() or not 1 <= int(number) <= len(fields):
                        print("Invalid field number.")
                        continue

                    field = fields[int(number) - 1]

                    if logic_manager.should_skip_field(profile, field):
                        print("This field does not apply to your current profile choices.")
                        continue

                    profile[field["key"]] = io_manager.ask_field(field)
                    changed = True

                    # Clear fields that no longer apply after this change.
                    for f in fields:
                        if logic_manager.should_skip_field(profile, f):
                            logic_manager.clear_field(profile, f)

                    # Ask for any newly required fields.
                    missing = logic_manager.find_missing_fields(profile, PROFILE_FIELDS)
                    if missing:
                        profile.update(io_manager.collect_missing(missing))

                    print("Field updated. You can edit another, or enter 0 to finish.")

                if changed:
                    if io_manager.confirm("Save these changes?"):
                        result = db.save_profile(profile)
                        print("Profile updated." if result["saved"] else result["message"])
                    else:
                        print("Changes discarded.")

            elif choice == "5":
                if io_manager.confirm("Permanently delete your account and matching records?"):
                    if db.delete_user(student_id) == 200:
                        print("Account deleted. Thank you for using SITogether, Goodbye!")
                        return
                    print("Deletion did not finish. Some records may have changed. Please retry.")
            
            elif choice == "6":
                            print("Thanks for using SITogether!")
                            return

            else:
                print("Please enter 1, 2, 3, 4, 5 or 6.")

        except Exception as error:
            print("Could not complete this option:", error)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")
    except Exception as error:
        print("Could not start the program:", error)
