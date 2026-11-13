from psycopg_pool import ConnectionPool


class OTPRepo:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create_otp(self, student_id: str, otp: int) -> bool:
        with self.pool.connection() as conn:
            delete_result = conn.execute(
                """
                DELETE FROM otp
                WHERE student_id = %s
                """,
                (student_id,),
            )
            result = conn.execute(
                """
        INSERT INTO otp (student_id, otp, created_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        RETURNING student_id
        """,
                (student_id, otp),
            ).fetchone()

            return result is not None

    def get_otp(self, student_id: str) -> int | None:
        with self.pool.connection() as conn:
            result = conn.execute(
                """
                SELECT otp 
                FROM otp
                WHERE student_id = %s
                  AND created_at > CURRENT_TIMESTAMP - INTERVAL '10 minutes'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (student_id,),
            ).fetchone()

            if result is None:
                return result

            otp = result.get("otp")

            return otp

    def delete_otp(self, student_id: str, expected_otp: int | None = None) -> bool:
        """Delete an OTP; when verifying, consume only the matching unexpired code."""
        query = "DELETE FROM otp WHERE student_id = %s"
        values = [student_id]
        if expected_otp is not None:
            query += " AND otp = %s AND created_at > CURRENT_TIMESTAMP - INTERVAL '10 minutes'"
            values.append(expected_otp)
        query += " RETURNING student_id"
        with self.pool.connection() as conn:
            result = conn.execute(query, values).fetchone()
            return result is not None
