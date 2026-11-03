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
print(f"Create user acc result: {create_acc_result}")
pool.close()  # Close the connection pool after the test
