from abc import ABC, abstractmethod
from models.user import User


class UserSource(ABC):
    @abstractmethod
    def get_user(self, student_id: str) -> User | None: ...

    @abstractmethod
    def get_candidates(self, student_id: str, exclude: set[str]) -> list[User]: ...


class SupabaseUserSource(UserSource):
    """Reads Users from Supabase (swap for a repo-backed source later)."""

    def __init__(self, supabase, table="users"):
        self._db = supabase
        self._table = table

    def get_user(self, student_id):
        res = self._db.table(self._table).select("*").eq("student_id", str(student_id)).execute()
        return User.from_dict(res.data[0]) if res.data else None

    def get_candidates(self, student_id, exclude):
        rows = (self._db.table(self._table).select("*")
                .neq("student_id", str(student_id)).order("student_id").execute().data or [])
        return [User.from_dict(r) for r in rows if str(r.get("student_id")) not in exclude]