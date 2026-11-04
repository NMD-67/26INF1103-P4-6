from services.user_service import UserService
from repositories.user_repo import UserRepo
from models.user import User
from Data_Manager.database.connection import create_connection_pool

pool = create_connection_pool()  # Assuming you have a ConnectionPool class defined somewhere
user_repo = UserRepo(pool)
user_service = UserService(user_repo)

# Test create user acc
test_user = User(student_id="1234567", name="TEST_ACC")
create_acc_result = user_service.login_user(test_user.student_id)
if create_acc_result.success:
    print(f"User logged in successfully")
else:
    print(f"Failed to log in user: {create_acc_result.error}")

# Test update user name
update_fields = {"name": "UPDATED_NAME"}
update_result = user_service.update_user(test_user.student_id, update_fields)
if update_result.success:
    print(f"User updated successfully")
else:
    print(f"Failed to update user: {update_result.error}")

# Test update user hobbies
update_hobbies_fields = {"hobbies": ["Reading", "Gaming", "Hiking"]}
update_hobbies_result = user_service.update_user(test_user.student_id, update_hobbies_fields)
if update_hobbies_result.success:
    print(f"User hobbies updated successfully")
else:
    print(f"Failed to update user hobbies: {update_hobbies_result.error}")

# Test get user
get_user_result = user_service.login_user(test_user.student_id)
if get_user_result.success:
    user = get_user_result.data
    user.print_user_details()  # Print user details for debugging
else:
    print(f"Failed to retrieve user: {get_user_result.error}")

# Test delete user
delete_result = user_service.delete_user(test_user.student_id)
if delete_result.success:
    print(f"User deleted successfully")
else:
    print(f"Failed to delete user: {delete_result.error}")

pool.close()  # Close the connection pool after the test
