from psycopg_pool import ConnectionPool
from psycopg.errors import UniqueViolation
from psycopg import rows, sql
from exceptions.duplicate_student_id import DuplicateStudentIdException
from models.user import User
from models.profile import Profile
from models.dealbreaker import DealBreaker
from config.user_fields import (
    USER_FIELD_CONFIG,
    LIST_FIELDS,
    CLASS_FIELDS,
    DEAL_BREAKER_CONFIG,
)

class UserRepo:
    """Repository class for user-related database operations"""

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _get_array_tables(self) -> list[str]:
        """Get a list of tables that store array data for users"""
        array_tables = []
        for key, value in USER_FIELD_CONFIG.items():
            if value["type"] == list and value.get("class") is None:
                array_tables.append(value["storage"])
        return array_tables

    def create(self, user: User) -> User:
        """Create a new user in the database."""
        try:
            with self.pool.connection() as conn:
                row = conn.execute(
                    """
          INSERT INTO users (student_id)
          VALUES (%s)
          RETURNING student_id
          """,
                    (user.student_id,),
                ).fetchone()

                return User(student_id=row["student_id"])
        except UniqueViolation as error:
            if error.diag.constraint_name == "users_student_id_key":
                raise DuplicateStudentIdException(
                    "Duplicate student ID found"
                ) from error
            raise

    def update(self, student_id: str, fields: dict) -> bool:
        """Update user details in the database. Parameters:
        student_id: str
        fields: dict{
        #Attributes to update eg.
        "name": str,
        "hobbies": list[str],
        "dealbreakers": DealBreakers
        }"""

        if not fields:
            return False

        array_fields = {
            field: value for field, value in fields.items() if field in LIST_FIELDS
        }

        class_fields = {
            field: value for field, value in fields.items() if field in CLASS_FIELDS
        }

        assignments = ", ".join(
            f"{field} = %s"
            for field in fields
            if field in USER_FIELD_CONFIG
            and field != "student_id"
            and USER_FIELD_CONFIG[field]["storage"] == "users"
            and USER_FIELD_CONFIG[field]["editable"]
        )

        # print("Assignments:", assignments)  # Debugging statement

        values = [
            fields[field]
            for field in fields
            if field in USER_FIELD_CONFIG
            and USER_FIELD_CONFIG[field]["storage"] == "users"
            and USER_FIELD_CONFIG[field]["editable"]
        ] + [student_id]

        query = f"""
      UPDATE users
      SET {assignments}
      WHERE student_id = %s
      RETURNING student_id
    """

        with self.pool.connection() as conn:
            result = None
            if assignments:
                result = conn.execute(query, values).fetchone()

            for field in array_fields:
                # delete fields that are not in the new list
                values = list(
                    dict.fromkeys(fields[field])
                )  # Remove duplicates while preserving order
                table_name = USER_FIELD_CONFIG[field]["storage"]
                column_name = USER_FIELD_CONFIG[field]["column_name"]
                # print(f"Deleting from {table_name} where student_id = {student_id} and {column_name} not in {array_fields[field]}")  # Debugging statement
                conn.execute(
                    f"""
                    DELETE FROM {table_name}
                    WHERE student_id = %s AND NOT({column_name} = ANY(%s))
                    """,
                    (student_id, values),
                )

                # insert new fields that are not in the old list
                result = conn.execute(
                    f"""
                    INSERT INTO {table_name} (student_id, {column_name})
                    SELECT %s, unnest(%s::text[])
                    ON CONFLICT (student_id, {column_name}) DO NOTHING
                    RETURNING student_id
                    """,
                    (student_id, array_fields[field]),
                )
            for field in class_fields:
                # Check if the provided class matches config class
                updated_values = fields[field]
                table_name = USER_FIELD_CONFIG[field]["storage"]
                is_list = USER_FIELD_CONFIG[field]["type"] == list
                column_names = list(updated_values)

                columns = ", ".join(column for column in column_names)
                values = list(updated_values.values())
                placeholders = ", ".join(["%s"] * len(values))
                sets = ", ".join(
                    f"{column} = EXCLUDED.{column}" for column in column_names
                )
                result = conn.execute(
                    f"""
                INSERT INTO {table_name} (student_id, {columns}) VALUES (%s, {placeholders})
                ON CONFLICT (student_id) DO UPDATE SET {sets}
                RETURNING student_id
                """,
                    (
                        student_id,
                        *values,
                    ),
                )

            return result is not None

    def get_user(self, student_id: str) -> User | None:
        with self.pool.connection() as conn:
            user_details = conn.execute(
                """
        SELECT *
        FROM users
        WHERE student_id = %s
        """,
                (student_id,),
            )
            row = user_details.fetchone()
            if not row:
                return None

            array_tables = self._get_array_tables()
            for table in array_tables:
                column_name = USER_FIELD_CONFIG[
                    next(
                        key
                        for key, value in USER_FIELD_CONFIG.items()
                        if value["storage"] == table
                    )
                ]["column_name"]
                array_result = conn.execute(
                    f"""
          SELECT *
          FROM {table}
          WHERE student_id = %s
          """,
                    (student_id,),
                )
                array_row = array_result.fetchall()
                if array_row:
                    row[table] = [item[column_name] for item in array_row]

            # print(f"Retrieved user details: {row}")  # Debugging statement

            return User.from_dict(dict(row))

    def get_profile(self, student_id: str) -> Profile | None:
        user = self.get_user(student_id)
        if user is not None:
            with self.pool.connection() as conn:
                row = conn.execute(
                    """
                    SELECT * 
                    FROM dealbreakers
                    WHERE student_id = %s
                    """,
                    (student_id,),
                ).fetchone()

                filtered_row = {
                    key: value
                    for key, value in (row or {}).items()
                    if key in DEAL_BREAKER_CONFIG
                }

                base_user = {
                    field: value for field, value in user.get_user_details().items()
                }

                return Profile(**base_user, dealbreakers=filtered_row)

    def delete(self, student_id: str) -> bool:
        with self.pool.connection() as conn:
            result = conn.execute(
                """
        DELETE FROM users
        WHERE student_id = %s
        RETURNING student_id
        """,
                (student_id,),
            ).fetchone()

            return result is not None

    def get_all_users(self) -> list[User]:
        """Load every user, including their array fields, using one query per table."""
        with self.pool.connection() as conn:
            rows = conn.execute("SELECT * FROM users").fetchall()
            users = {row["student_id"]: dict(row) for row in rows}

            for table in self._get_array_tables():
                key = next(k for k, v in USER_FIELD_CONFIG.items() if v["storage"] == table)
                column_name = USER_FIELD_CONFIG[key]["column_name"]

                array_rows = conn.execute(
                    f"SELECT student_id, {column_name} FROM {table}"
                ).fetchall()

                for item in array_rows:
                    sid = item["student_id"]
                    if sid in users:
                        users[sid].setdefault(table, []).append(item[column_name])

            return [
        User.from_dict({**data, "age": (data.get("age"))})
        for data in users.values()
      ]

    def get_dealbreaker(self, student_id: str) -> dict | None:
        """Return the dealbreaker row for a student, or None if they haven't set any."""
        with self.pool.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM dealbreakers
                WHERE student_id = %s
                """,
                (student_id,)
            ).fetchone()

    @staticmethod
    def _overlaps(value, allowed: list) -> bool:
        """True if the user's value (a single item or a list) shares anything with the allowed list."""
        if value is None:
            return False
        values = value if isinstance(value, (list, tuple, set)) else [value]
        return bool(set(values) & set(allowed))
    
    def get_users_by_dealbreaker(self, student_id: str) -> list[User]:
        """Return users who satisfy the given student's dealbreakers."""
        users = [u for u in self.get_all_users() if u.student_id != student_id]

        dealbreaker = self.get_dealbreaker(student_id)
        if not dealbreaker:
            return users

        # 1. gender
        gender = dealbreaker.get("gender")
        if gender:
            users = [u for u in users if u.gender == gender]

        # 2. age
        min_age = dealbreaker.get("min_age")
        max_age = dealbreaker.get("max_age")
        if min_age is not None or max_age is not None:
            def in_range(u):
                age = u.age
                return (
                    age is not None
                    and (min_age is None or age >= min_age)
                    and (max_age is None or age <= max_age)
                )
            users = [u for u in users if in_range(u)]

        # 3. religion
        religions = dealbreaker.get("religion") or []
        if religions:
            users = [u for u in users if not self._overlaps(u.religion, religions)]

        # 4. race
        races = dealbreaker.get("race") or []
        if races:
            users = [u for u in users if not self._overlaps(u.race, races)]

        return users
    def test():
        """Test method to verify the functionality of the UserRepo class."""
        # Implement test cases here
        print("Running UserRepo tests...")
        pass