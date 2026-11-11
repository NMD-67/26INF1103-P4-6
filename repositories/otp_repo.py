from psycopg_pool import ConnectionPool


class OTPRepo:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create_otp(self, student_id: str, otp: int) -> bool:
        with self.pool.connection() as conn:
            result = conn.execute(
                """
        INSERT INTO otp (student_id, otp)
        VALUES (%s, %s)
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
                ORDER BY created_at DESC
                """,
                (student_id,),
            ).fetchone()

            if result is None:
                return result

            otp = result.get("otp")

            return otp
