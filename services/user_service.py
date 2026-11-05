from exceptions.duplicate_student_id import DuplicateStudentIdException
from results.result import Result
from results.success import Success
from results.error import Error
from repositories.user_repo import UserRepo
from models.user import User
from models.dealbreaker import DealBreaker

class UserService:
  def __init__(self, user_repo: UserRepo):
    self.user_repo = user_repo

  def login_user(self, student_id: str) -> Result:
    user = self.user_repo.get_user(student_id)
    if user:
      return Success(user)

    try:
      new_user = self.user_repo.create(User(student_id=student_id))
      if new_user:
        return Success(new_user)
    except DuplicateStudentIdException as e:
      return Error(str(e))
    
  def update_user(self, student_id: str, fields: dict) -> Result:
    update_user_result = self.user_repo.update(student_id, fields)
    if update_user_result is None:
      return Error(f"User with student_id {student_id} not found")
    return Success(f"User with student_id {student_id} updated successfully")

  def get_user(self, student_id: str) -> Result:
    user = self.user_repo.get_user(student_id)
    if user:
      return Success(user)
    return Error(f"User with student_id {student_id} not found")
  
  def delete_user(self, student_id: str) -> Result:
    delete_user_result = self.user_repo.delete(student_id)
    if delete_user_result is None:
      return Error(f"User with student_id {student_id} not found")
    return Success(f"User with student_id {student_id} deleted successfully")

  def filter_users_by_dealbreaker(self, student_id: str) -> Result:
    """Returns an array of users that fit the criteria for the student's deal breakers, used to feed the AI for matchmaking processing"""
    # TODO: Val/Raph   
    # Call the user_repo method
    # Check if user array is empty
    # If empty, return error
    # else return success with list[User] as data

    