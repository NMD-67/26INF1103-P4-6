

from psycopg_pool import ConnectionPool
from psycopg.errors import UniqueViolation
from exceptions.duplicate_student_id import DuplicateStudentIdException
from models.user import User


class UserRepo:
  """Repository class for user-related database operations"""
  def __init__(self, pool: ConnectionPool):
    self.pool = pool

  def create(self, user: User) -> User:
    """Create a new user in the database"""
    try:
      with self.pool.connection() as conn:
        row = conn.execute(
          """
          INSERT INTO users (student_id)
          VALUES (%s)
          RETURNING student_id
          """,
          (user.student_id,)
          ).fetchone()

        return User(
          student_id=row[0]
        )
    except UniqueViolation as error:
      if error.diag.constraint_name == "users_student_id_key":
        raise DuplicateStudentIdException("Duplicate student ID found") from error
      raise

  def update(self, student_id: str, fields: dict) -> bool:
    if not fields:
      return False

    #TODO: Add fields varification (Ensure fields are valid and can be edited)
    assignments = ", ".join(
      f"{field} = %s" for field in fields
    )

    values = list(fields.values()) + [student_id]

    query = f"""
      UPDATE users
      SET {assignments}
      WHERE student_id = %s
      RETURNING student_id
    """

    with self.pool.connection() as conn:
      result = conn.execute(query, values).fetchone()

      return result is not None

  def get_user(self, student_id: str) -> User | None:
    with self.pool.connection() as conn:
      user_details = conn.execute(
        """
        SELECT *
        FROM users
        WHERE student_id = %s
        """,
        (student_id,)
      )
      row = user_details.fetchone()
      if not row:
        return None

      return User(
        student_id=row[0]
      )
