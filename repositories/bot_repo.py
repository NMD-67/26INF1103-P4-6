from psycopg_pool import ConnectionPool


class BotRepo:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def add_bot(self, bot_id: str, student_id: str) -> bool:
        with self.pool.connection() as conn:
            result = conn.execute(
                """
        INSERT INTO bot_users (tele_id, student_id)
        VALUES (%s, %s)
        ON CONFLICT (tele_id) DO NOTHING
        RETURNING student_id
        """,
                (bot_id, student_id),
            ).fetchone()

            return result is not None

    def get_student_id(self, bot_id: str) -> str | None:
        with self.pool.connection() as conn:
            result = conn.execute(
                """
              SELECT * 
              FROM bot_users 
              WHERE tele_id = %s
                """,
                (bot_id,),
            ).fetchone()

            student_id = result.get("student_id")
            return student_id
