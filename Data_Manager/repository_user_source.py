"""Read fully populated profiles using the shared mutual-preference filter."""
from Data_Manager.user_source import UserSource


class RepositoryUserSource(UserSource):
    def __init__(self, user_repo):
        self._users = user_repo

    def get_user(self, student_id):
        return self._users.get_user(student_id)

    def get_candidates(self, student_id, exclude):
        excluded = {str(value) for value in exclude}
        excluded.add(str(student_id))
        return [user for user in self._users.get_users_by_dealbreaker(student_id)
                if str(user.student_id) not in excluded]
