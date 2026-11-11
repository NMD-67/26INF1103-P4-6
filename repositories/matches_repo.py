from psycopg_pool import ConnectionPool

from models.candidate import Candidate
from models.user import User
from models.match import Match
from config.user_fields import SCALAR_FIELDS, LIST_FIELDS
from config.user_fields import REPOSITORY_FIELD_CONFIG as USER_FIELD_CONFIG


class MatchesRepo:
    """Repository class for matches-related database operations"""

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _group(
        self, conn, table: str, column: str, student_id_list: list[str]
    ) -> dict[str, list[str]]:
        result = {}
        for query_result in conn.execute(
            f"""
          SELECT student_id, {column}
          FROM {table}
          WHERE student_id = ANY(%s)
          """,
            (student_id_list,),
        ).fetchall():
            result.setdefault(query_result["student_id"], []).append(
                query_result[column]
            )
        return result

    def create_match(
        self,
        student_id: str,
        candidate_id: str,
        compatibility_score: float,
        reason: str = None,
    ) -> bool:
        """Create a new match in the database."""
        # TODO: Decide on the handling of dupes (Ignore/edit?) [Marrisa]
        with self.pool.connection() as conn:
            result = conn.execute(
                """
              INSERT INTO matches (student_id, candidate_id, compatibility_score, reason, status)
              VALUES (%s, %s, %s, %s, 'pending')
              ON CONFLICT (student_id, candidate_id) 
              DO UPDATE SET student_id = EXCLUDED.student_id
              RETURNING student_id
              """,
                (student_id, candidate_id, compatibility_score, reason),
            ).fetchone()
        return result is not None

    def get_candidates_for_user(
        self, student_id: str, fetch_one: bool = False
    ) -> list[Candidate]:
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
                (student_id,),
            )

            candidate_result = (
                candidate_result.fetchone()
                if fetch_one
                else candidate_result.fetchall()
            )

            if not isinstance(candidate_result, list):
                candidate_result = [candidate_result]

            candidate_list = [
                Candidate.from_dict(dict(row)) for row in candidate_result
            ]

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
                    (candidate_id_list,),
                ).fetchall()

                for row in array_result:
                    if row["student_id"] in candidate_id_list:
                        candidate = next(
                            (
                                c
                                for c in candidate_list
                                if c.student_id == row["student_id"]
                            ),
                            None,
                        )
                        if candidate:
                            if not hasattr(candidate, field):
                                setattr(candidate, field, [])
                            getattr(candidate, field).append(row[column_name])

        return candidate_list if candidate_list else []

    def edit_status(self, student_id: str, candidate_id: str, new_status: str) -> bool:
        """
        Change the status of a student_id candidate_id pair in the matches table
        """
        valid_statuses = ["accepted", "rejected", "pending"]
        if new_status not in valid_statuses:
            return False
        with self.pool.connection() as conn:
            result = conn.execute(
                """
              UPDATE matches
              SET status = %s
              WHERE student_id = %s AND candidate_id = %s
              RETURNING status
              """,
                (new_status, student_id, candidate_id),
            )

            # UPDATE ... RETURNING yields a row only when a record was updated.
            return result.fetchone() is not None

    def get_match_status(self, student_id: str, candidate_id: str) -> str | None:
        """Get this student's status for a particular candidate."""
        with self.pool.connection() as conn:
            row = conn.execute(
                """
                SELECT status
                FROM matches
                WHERE student_id = %s AND candidate_id = %s
                """,
                (student_id, candidate_id),
            ).fetchone()
        return row["status"] if row else None

    def get_accepted_students(self, student_id: str) -> list[str]:
        """Get all candidate IDs this student has accepted."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT candidate_id
                FROM matches
                WHERE student_id = %s AND status = 'accepted'
                """,
                (student_id,),
            ).fetchall()
        return [str(row["candidate_id"]) for row in rows]

    def get_candidate_with_highest_score(self, student_id: str) -> Candidate | None:
        """
        Finds the candidate with the highest score for student.
        TODO: Teammate's original implementation is not yet provided.
        """
        return None

    def get_matches_for_user(self, student_id: str) -> list[Match] | None:
        """
        Returns a list of matches for the user, returns None if an error.
        TODO: Teammate's original implementation is not yet provided.
        """
        matches_list = []
        user_table_fields = ["u." + field for field in SCALAR_FIELDS]
        user_fields_str = ", ".join(user_table_fields)
        with self.pool.connection() as conn:
            matches_result = conn.execute(
                f"""
              SELECT {user_fields_str}
              FROM matches m
              JOIN matches r ON m.student_id = r.candidate_id AND r.student_id = m.candidate_id
              JOIN users u ON u.student_id = m.candidate_id
              WHERE m.student_id = %s 
              AND m.status = 'accepted'
              AND r.status = 'accepted'
              ORDER BY m.compatibility_score DESC
              """,
                (student_id,),
            ).fetchall()

            matches_list = [Match.from_dict(dict(row)) for row in matches_result]

            matches_id_list = [row["student_id"] for row in matches_result]
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
                    (matches_id_list,),
                ).fetchall()

                for row in array_result:
                    if row["student_id"] in matches_id_list:
                        match = next(
                            (
                                student
                                for student in matches_list
                                if student.student_id == row["student_id"]
                            ),
                            None,
                        )
                        if match:
                            if not hasattr(match, field):
                                setattr(match, field, [])
                            getattr(match, field).append(row[column_name])

        return matches_list if matches_list else []
