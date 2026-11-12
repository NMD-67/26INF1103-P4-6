from models import User  # adjust to wherever your User class lives


class Candidate(User):
    """A suggested match for a student.

    Inherits the candidate's own profile fields from User and adds the
    match-specific data stored in the `candidates` table.
    """

    TABLE = "candidates"

    def __init__(
        self,
        row_id: int,
        student_id: str,          # the student the candidate is suggested TO
        candidate_id: str,        # the suggested person (their User.student_id)
        compatibility_score: int,
        reason: str,
        status: str = "pending",  # pending / accepted / rejected
        created_at=None,
        db=None,                  # supabase client, injected
        **user_fields,            # remaining User attributes of the candidate
    ):
        super().__init__(student_id=candidate_id, **user_fields)
        self.id = row_id
        self.viewer_id = student_id
        self.compatibility_score = compatibility_score
        self.reason = reason
        self.status = status
        self.created_at = created_at
        self._db = db

    @classmethod
    def from_row(cls, row: dict, user_row: dict, db=None) -> "Candidate":
        """Build from a `candidates` row plus the candidate's `users` row."""
        return cls(
            row_id=row["id"],
            student_id=row["student_id"],
            candidate_id=row["candidate_id"],
            compatibility_score=row["compatibility_score"],
            reason=row["reason"],
            status=row["status"],
            created_at=row["created_at"],
            db=db,
            **{k: v for k, v in user_row.items() if k != "student_id"},
        )

    def get_user_details(self) -> dict:
        details = super().get_user_details()
        details.update(
            {
                "compatibility_score": self.compatibility_score,
                "reason": self.reason,
                "status": self.status,
            }
        )
        return details

    def handle_decision(self, accepted: bool) -> None:
        self.status = "accepted" if accepted else "rejected"
        if self._db is not None:
            (
                self._db.table(self.TABLE)
                .update({"status": self.status})
                .eq("id", self.id)
                .execute()
            )