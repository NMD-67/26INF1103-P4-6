from exceptions.duplicate_student_id import DuplicateStudentIdException
from results.result import Result
from results.success import Success
from results.error import Error
from repositories.user_repo import UserRepo
from models.user import User


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
    pass
    