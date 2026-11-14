# Abstract interface defining how users and candidates are loaded, independent of the data store.

from abc import ABC, abstractmethod

from models.user import User

class UserSource(ABC):
    @abstractmethod
    def get_user(self, student_id: str) -> User | None: ...

    @abstractmethod
    def get_candidates(self, student_id: str, exclude: set[str]) -> list[User]: ...