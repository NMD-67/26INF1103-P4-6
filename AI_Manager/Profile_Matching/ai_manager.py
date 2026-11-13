"""Adapt the shared scoring functions to the main application's interface."""
from types import SimpleNamespace

from AI_Manager.Profile_Matching.scoring import get_compatibility_score


class AIManager:
    def __init__(self, client):
        self._client = client

    def match_candidates(self, main_user, candidates):
        matches = []
        for candidate in candidates:
            if candidate.student_id == main_user.student_id:
                continue
            score, reason = get_compatibility_score(
                self._client, main_user, candidate
            )
            if score is None:
                continue
            matches.append(SimpleNamespace(
                matched_user=candidate.student_id,
                compatibility_score=score,
                reason=reason,
            ))
        matches.sort(key=lambda match: match.compatibility_score, reverse=True)
        return matches
