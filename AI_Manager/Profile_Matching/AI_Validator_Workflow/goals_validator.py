
from .category_validator import CategoryValidator


class GoalsValidator(CategoryValidator):
    """
    Rule-based relationship goals validator.

    Checks:
    1. Mutual gender preferences
    2. Relationship intentions
    3. Shared expectations and values

    Returns a compatibility score from 0 to 100.
    No AI models or external APIs required.
    """

    category = "relationship_goals"

    NO_PREFERENCE = {
        "", "any", "all", "both",
        "everyone", "no preference"
    }

    # Relationship intention compatibility matrix
    
    GOAL_SCORES = {
        ("both", "both"): 90,
        ("both", "relationship"): 80,
        ("both", "friends"): 55,

        ("relationship", "relationship"): 90,
        ("relationship", "friends"): 15,

        ("friends", "friends"): 90
    }

    # Keywords representing shared relationship values
    VALUE_KEYWORDS = {
        "adventure": [
            "adventure", "exploring", "explore",
            "spontaneous", "travel", "new experiences"
        ],
        "communication": [
            "honest", "communication",
            "conversations", "talk", "open"
        ],
        "friendship": [
            "friendship", "friends", "friend"
        ],
        "commitment": [
            "serious", "long-term", "commitment",
            "relationship"
        ],
        "fun": [
            "fun", "laughter", "playful",
            "humour", "humor"
        ],
        "activities": [
            "games", "gaming", "sports",
            "activities", "outings"
        ]
    }

    def validate_batch(self, main_user, candidates):
        """
        Validate multiple candidates against the main user.
        """
        return [
            self.validate(main_user, candidate)
            for candidate in candidates
        ]

    def validate(self, main_user, candidate):
        """
        Calculate deterministic compatibility score.
        """

        # Step 1: Check mutual gender preferences
        if not self._mutual_preference(main_user, candidate):
            return 10

        # Step 2: Calculate relationship intention score
        main_goal = self._normalise_goal(
            main_user.here_for
        )

        candidate_goal = self._normalise_goal(
            candidate.here_for
        )

        if main_goal is None or candidate_goal is None:
            return None

        goal_score = self._goal_compatibility(
            main_goal, candidate_goal
        )

        # Step 3: Compare written expectations
        expectation_bonus = self._compare_expectations(
            main_user.expectations,
            candidate.expectations
        )

        # Step 4: Final compatibility score
        final_score = goal_score + expectation_bonus

        return max(0, min(100, final_score))

    def _mutual_preference(self, main_user, candidate):
        """
        Both users must satisfy each other's gender preferences.
        """
        return (
            self._fits(
                main_user.match_preference,
                candidate.gender
            )
            and self._fits(
                candidate.match_preference,
                main_user.gender
            )
        )

    def _fits(self, preference, gender):
        preference = (preference or "").strip().lower()
        gender = (gender or "").strip().lower()

        if preference in self.NO_PREFERENCE:
            return True

        if not gender:
            return False

        return preference == gender

    def _normalise_goal(self, goal):
        """
        Normalise database relationship intentions.
        """
        if not goal:
            return None

        goal = goal.strip().lower()

        mapping = {
            "both": "both",
            "friends": "friends",
            "friendship": "friends",
            "friend": "friends",
            "relationship": "relationship",
            "dating": "relationship",
            "romantic": "relationship"
        }

        return mapping.get(goal)

    def _goal_compatibility(self, goal_a, goal_b):
        """
        Look up compatibility score regardless of user order.
        """
        if (goal_a, goal_b) in self.GOAL_SCORES:
            return self.GOAL_SCORES[(goal_a, goal_b)]

        return self.GOAL_SCORES.get(
            (goal_b, goal_a), 50
        )

    def _compare_expectations(self, text_a, text_b):
        """
        Award up to 10 bonus points for shared values.
        """
        if not text_a or not text_b:
            return 0

        values_a = self._extract_values(text_a)
        values_b = self._extract_values(text_b)

        shared_values = values_a.intersection(values_b)

        # 5 points per shared value, maximum 10
        return min(len(shared_values) * 5, 10)

    def _extract_values(self, text):
        """
        Identify relationship values using keywords.
        """
        text = text.lower()
        detected = set()

        for category, keywords in self.VALUE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                detected.add(category)

        return detected
