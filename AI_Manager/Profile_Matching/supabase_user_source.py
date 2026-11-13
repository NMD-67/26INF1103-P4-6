# Concrete user source that reads User objects from the Supabase users table.

import os

from supabase import create_client

from models.user import User
from .user_source import UserSource


class SupabaseUserSource(UserSource):
    def __init__(self, supabase, table="users"):
        self._db = supabase
        self._table = table

    @classmethod
    def from_env(cls):
        url, key = os.getenv("SUPABASE_API_URL"), os.getenv("SUPABASE_API_KEY")
        if not url or not key:
            raise RuntimeError("Set SUPABASE_API_URL and SUPABASE_API_KEY in .env")
        return cls(create_client(url, key))

    def get_user(self, student_id):
        res = (self._db.table(self._table).select("*")
               .eq("student_id", str(student_id)).execute())
        return User.from_dict(res.data[0]) if res.data else None

    def get_candidates(self, student_id, exclude):
        rows = (self._db.table(self._table).select("*")
                .neq("student_id", str(student_id)).order("student_id")
                .execute().data or [])
        return [User.from_dict(r) for r in rows if str(r.get("student_id")) not in exclude]