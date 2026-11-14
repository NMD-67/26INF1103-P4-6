from Data_Manager.repositories.matches_repo import MatchesRepo
from Logic_Manager.services.match_service import MatchService
from Logic_Manager.services.user_service import UserService
from Data_Manager.repositories.user_repo import UserRepo
from models.user import User
from Data_Manager.database.connection import create_connection_pool
from models.dealbreaker import DealBreaker
from Data_Manager.repositories.otp_repo import OTPRepo

pool = (
    create_connection_pool()
)  # Assuming you have a ConnectionPool class defined somewhere
user_repo = UserRepo(pool)
user_service = UserService(user_repo)
match_repo = MatchesRepo(pool)
match_service = MatchService(match_repo)
otp_repo = OTPRepo(pool)

test_user = User(student_id="1234567", name="TEST_ACC")
test_user2 = User(student_id="7654321", name="TEST_ACC_2")


# Test OTP
def otp_test():
    otp_repo.create_otp("1234567", "6767")
    otp_repo.get_otp("1234567")


# Test create user acc
def create_acc_test():
    create_acc_result = user_service.login_user(test_user.student_id)
    if create_acc_result.success:
        print(f"User logged in successfully")
    else:
        print(f"Failed to log in user: {create_acc_result.error_msg}")


# Test update user name
def test_update_name():
    update_fields = {"name": "UPDATED_NAME"}
    update_result = user_service.update_user(test_user.student_id, update_fields)
    if update_result.success:
        print(f"User updated successfully")
    else:
        print(f"Failed to update user: {update_result.error_msg}")


# Test update user hobbies
def test_update_array():
    update_hobbies_fields = {"hobbies": ["Reading", "Gaming", "Hiking"]}
    update_hobbies_result = user_service.update_user(
        test_user.student_id, update_hobbies_fields
    )
    if update_hobbies_result.success:
        print(f"User hobbies updated successfully")
    else:
        print(f"Failed to update user hobbies: {update_hobbies_result.error_msg}")


# Test update dealbreakers
def test_update_class():
    new_dealbreakers = DealBreaker(
        min_age=6,
        max_age=7,
        religion=["Muslim", "Christian"],
        race=["Malay", "Indian"],
        gender="Male",
    )
    update_dealbreakers_result = user_service.update_user(
        test_user.student_id,
        {
            "dealbreakers": {
                "min_age": 6,
                "max_age": 67,
                "religion": ["Muslim", "Christian"],
                "race": ["Malay", "Indian"],
                "gender": "Male",
            }
        },
    )
    if update_dealbreakers_result.success:
        print(f"User dealbreakers updated success")
    else:
        print(f"Failed to update user hobbies: {update_dealbreakers_result.error_msg}")


# Test get user profile
def test_get_profile():
    get_user_result = user_service.get_profile(test_user.student_id)
    if get_user_result.success:
        user = get_user_result.data
        user.print_user_details()  # Print user details for debugging
    else:
        print(f"Failed to retrieve user: {get_user_result.error_msg}")


# Test create match
def test_create_match(
    student_id: str = test_user.student_id, candidate_id: str = test_user2.student_id
):
    create_acc_result2 = user_service.login_user(test_user2.student_id)
    if create_acc_result2.success:
        print(f"Second user logged in successfully")
    else:
        print(f"Failed to log in second user: {create_acc_result2.error_msg}")
    create_match_result = match_service.create_match(
        student_id,
        candidate_id,
        85,
        "Good compatibility based on shared interests",
    )
    if create_match_result.success:
        print(f"Match created successfully")
    else:
        print(f"Failed to create match: {create_match_result.error_msg}")


def test_update_bulk():
    edit_fields_user2 = {"name": "UPDATED_NAME_2", "hobbies": ["Cooking", "Traveling"]}
    update_user2_result = user_service.update_user(
        test_user2.student_id, edit_fields_user2
    )
    if update_user2_result.success:
        print(f"Second user updated successfully")
    else:
        print(f"Failed to update second user: {update_user2_result.error_msg}")


# Test get candidates for user
def test_get_candidates():
    candidates_result = match_service.get_candidates_for_user(test_user.student_id)
    if candidates_result.success:
        candidates = candidates_result.data
        print(f"Candidates for user {test_user.student_id}:")
        for candidate in candidates:
            print(
                f"Candidate ID: {candidate.student_id}, Name: {candidate.name}, Compatibility Score: {candidate.compatibility_score}, Reason: {candidate.reason}"
            )
            candidate.print_user_details()  # Print candidate details for debugging
    else:
        print(f"Failed to retrieve candidates: {candidates_result.error_msg}")


def test_handle_decision():
    descision_result = match_service.handle_candidate_decision(
        student_id=test_user2.student_id,
        candidate_id=test_user.student_id,
        accepted=True,
    )
    if descision_result.success:
        print("Candidate decision success")
    else:
        print(descision_result.error_msg)


def test_show_matches():
    matches_result = match_service.get_all_matches(test_user.student_id)
    if matches_result.success:
        print(f"Matches found: {matches_result.data}")
    else:
        print(matches_result.error_msg)


test_show_matches()
# Test delete user
# delete_result = user_service.delete_user(test_user.student_id)
# if delete_result.success:
#     print(f"User deleted successfully")
# else:
#     print(f"Failed to delete user: {delete_result.error_msg}")

pool.close()  # Close the connection pool after the test
