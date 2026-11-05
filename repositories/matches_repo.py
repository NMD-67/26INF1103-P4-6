from psycopg_pool import ConnectionPool

from models.candidate import Candidate
from models.user import User
from config.user_fields import SCALAR_FIELDS, USER_FIELD_CONFIG, LIST_FIELDS

class MatchesRepo:
  """Repository class for matches-related database operations"""
  def __init__(self, pool: ConnectionPool):
      self.pool = pool

  def _group(self, conn, table: str, column: str, student_id_list: list[str]) -> dict[str, list[str]]:
      result = {}
      for query_result in conn.execute(
          f"""
          SELECT student_id, {column}
          FROM {table}
          WHERE student_id = ANY(%s)
          """,
          (student_id_list,)
      ).fetchall():
          result.setdefault(query_result["student_id"], []).append(query_result[column])
      return result
      

  def create_match(self, student_id: str, candidate_id: str, compatibility_score: float, reason: str = None) -> bool:
      """Create a new match in the database."""
      # TODO: Decide on the handling of dupes (Ignore/edit?)
      with self.pool.connection() as conn:
          result = conn.execute(
              """
              INSERT INTO matches (student_id, candidate_id, compatibility_score, reason, status)
              VALUES (%s, %s, %s, %s, 'pending')
              ON CONFLICT (student_id, candidate_id) DO NOTHING
              RETURNING student_id
              """,
              (student_id, candidate_id, compatibility_score, reason)
          ).fetchone()
      return result is not None

  def get_candidates_for_user(self, student_id: str) -> list[Candidate]:
      """Retrieve candidates for a specific user."""
      candidate_list = []
      user_table_fields = ["u." + field for field in SCALAR_FIELDS]
      user_fields_str = ", ".join(user_table_fields)
      with self.pool.connection() as conn:
          candidate_result = conn.execute(
              f"""
              SELECT {user_fields_str}, m.compatibility_score, m.status, m.reason
              FROM matches m
              JOIN users u ON m.candidate_id = u.student_id
              WHERE m.student_id = %s 
              ORDER BY m.compatibility_score DESC
              """,
              (student_id,)
          ).fetchall()

          candidate_list = [Candidate.from_dict(dict(row)) for row in candidate_result]

          candidate_id_list = [row["student_id"] for row in candidate_result]
          array_fields = [field for field in LIST_FIELDS]

          for field in array_fields:
              table_name = USER_FIELD_CONFIG[field]["storage"]
              column_name = USER_FIELD_CONFIG[field]["column_name"]
              array_result = conn.execute(
                  f"""
                  SELECT student_id, {column_name}
                  FROM {table_name}
                  WHERE student_id = ANY(%s)
                  """,
                  (candidate_id_list,)
              ).fetchall()

              for row in array_result:
                  if row["student_id"] in candidate_id_list:
                      candidate = next((c for c in candidate_list if c.student_id == row["student_id"]), None)
                      if candidate:
                          if not hasattr(candidate, field):
                              setattr(candidate, field, [])
                          getattr(candidate, field).append(row[column_name])

      return candidate_list if candidate_list else []