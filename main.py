import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from database import db
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
    student_id = input("Enter your student ID: ").strip()

    if not auth.is_valid_student_id(student_id):
        print("Please enter a 7-digit student ID.")
        return

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
                if db.read_profile(student_id, sheet_name="matches") is None:
                    if db.add_user_matches_row(student_id) != 200:
                        print("Could not create your matching record.")
                        continue

                accepted = db.get_accepted_student_id(student_id)
                rejected = db.get_rejected_student_id(student_id)
                if not accepted["success"] or not rejected["success"]:
                    print("Could not read your previous decisions.")
                    continue

                print("Finding compatible profiles. Please wait...")
                client = profile_matching_AI.get_groq_client()
                try:
                    results = profile_matching_AI.AI_Profile_Matching(student_id, client)
                finally:
                    client.close()

                recommendations = []
                for result in results:
                    target_id = str(result["user_id"])
                    if (
                        target_id != student_id
                        and target_id not in accepted["accepted_student_id"]
                        and target_id not in rejected["rejected_student_id"]
                    ):
                        recommendations.append(result)

                if not recommendations:
                    print("No new recommendations returned. Check any AI errors above.")
                    continue
                if profile_matching_AI.Add_To_Database(student_id, recommendations) != 200:
                    print("Could not save recommendations.")
                    continue

                # Load saved recommendations.
                saved_matches = matching_logic.load_matches(student_id)
                if saved_matches is None:
                    print("Could not load recommendations. Please try again.")
                    continue
            
                profiles_to_show = []

                for target_id, score in saved_matches.items():
                    target_id = str(target_id)

                    if target_id == student_id:
                        continue

                    if target_id in accepted["accepted_student_id"]:
                        continue

                    if target_id in rejected["rejected_student_id"]:
                        continue

                    if matching_logic.compatibility_label(score) is None:
                        continue

                    profiles_to_show.append((target_id, int(score)))

                # Start browsing from the first profile.
                profiles_to_show = matching_logic.sort_matches_by_score(
                    dict(profiles_to_show)
                )
                matching_logic.current_match = 0
                new_connections = []

                if not profiles_to_show:
                    print("No new profiles to show.")

                while True:
                    item = matching_logic.show_next_match(profiles_to_show)

                    if item is False:
                        break

                    matched_profile, score = item

                    # Skip profiles that have been deleted.
                    if not matched_profile:
                        continue

                    target_id = str(matched_profile["student_id"])

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
                    result = asyncio.run(
                        matchmaking_ai.generate_suggestions_async(yours, theirs)
                    )
                    result["user_a_info"] = yours
                    result["user_b_info"] = theirs
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
                fields = [field for field in PROFILE_FIELDS if field["key"] != "student_id"]
                for number, field in enumerate(fields, start=1):
                    print(f"{number}. {io_manager.profile_label(field['key'])}")
                number = input("Choose a field to update (0 to return): ").strip()
                if number == "0":
                    continue
                if not number.isdigit() or not 1 <= int(number) <= len(fields):
                    print("Invalid field number.")
                    continue
                field = fields[int(number) - 1]
                if logic_manager.should_skip_field(profile, field):
                    print("This field does not apply to your current profile choices.")
                    continue
                profile[field["key"]] = io_manager.ask_field(field)
                for field in fields:
                    if logic_manager.should_skip_field(profile, field):
                        profile[field["key"]] = [] if field["kind"] == "list" else None
                missing = logic_manager.find_missing_fields(profile, PROFILE_FIELDS)
                if missing:
                    profile.update(io_manager.collect_missing(missing))
                if io_manager.confirm("Save these changes?"):
                    result = db.save_profile(profile)
                    print("Profile updated." if result["saved"] else result["message"])

            elif choice == "5":
                if io_manager.confirm("Permanently delete your account and matching records?"):
                    if db.delete_user(student_id) == 200:
                        print("Account deleted. Goodbye!")
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
