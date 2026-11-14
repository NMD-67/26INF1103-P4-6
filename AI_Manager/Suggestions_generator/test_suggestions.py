"""Run from project root: py -3.14 -m AI_Manager.Suggestions_generator.test_suggestions"""

from AI_Manager.Suggestions_generator import SuggestionsGenerator

from Logic_Manager.services.connection_suggestion_service import ConnectionSuggestionService


def main():

    from Data_Manager.database.connection import create_connection_pool
    from Data_Manager.repositories.user_repo import UserRepo
    from Data_Manager.repositories.matches_repo import MatchesRepo
    from Logic_Manager.services.user_service import UserService
    from Logic_Manager.services.match_service import MatchService

    USER_ID = "2604747"  # Set to a student with an existing mutual match.
    pool = create_connection_pool()
    try:
        users = UserService(UserRepo(pool))
        matches = MatchService(MatchesRepo(pool))
        generator = SuggestionsGenerator.from_environment()
        service = ConnectionSuggestionService(matches, users, generator)
        results = service.get_matches_for_user(USER_ID)
        if not results:
            print("No mutual matches found for this student.")
        for result in results:
            print("\n" + "=" * 50)
            if not result.get("success"):
                print("Error:", result.get("error"))
                continue
            other = result["user_b_info"]
            print("Matched with:", other.get("name"))
            print("Student ID:", result["user_b"])
            for title, key in (
                ("COMMON INTERESTS", "common_interests"),
                ("CONVERSATION STARTERS", "conversation_starters"),
                ("OUTING IDEAS", "outing_ideas"),
            ):
                print("\n" + title)
                for item in result[key]:
                    print("-", item)
    finally:
        pool.close()


if __name__ == "__main__":
    main()
