import sys
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch


# ============================================================
# ALLOW IMPORTS FROM PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORT REAL PROJECT FILES
# ============================================================

import main
from IO_Manager import io_manager
from Logic_Manager import logic_manager
from AI_Manager import profile_matching_AI
from AI_Manager import matchmaking_ai

from Data_Manager.database import db
from src import auth
from src import matches
from Logic_Manager.Matching import matching_logic
from IO_Manager.profile_schema import PROFILE_FIELDS


# ============================================================
# TEST ACCOUNT
# ============================================================

TEST_USER = "9000001"
TEST_OTP = "123456"


# ============================================================
# FAKE PROFILE DATABASE
# ============================================================

PROFILES = {
    TEST_USER: {
        "student_id": TEST_USER,
        "name": "Test User",
        "birthday": "01/01/2005",
        "gender": "Male",
        "year": "1",
        "course": "Applied Artificial Intelligence",
        "bio": "I enjoy technology, anime and going to the gym.",
        "religion": None,
        "mbti": "INTJ",
        "match_preference": "Both",
        "here_for": "Both",
        "expectations": "Looking to meet new people.",
        "telegram_handle": "@testuser",
        "insta_handle": "@testuser",
        "ccas": ["Track and Field"],
        "events": ["Orientation"],
        "hobbies": ["Gym", "Anime", "Technology"],
        "interest_groups": ["AI"],
        "profile_complete": True,
    }
}


# ============================================================
# 25 FAKE USERS
# ============================================================

NAMES = [
    "Alex",
    "Jamie",
    "Taylor",
    "Morgan",
    "Jordan",
    "Casey",
    "Avery",
    "Riley",
    "Skyler",
    "Cameron",
    "Dylan",
    "Harper",
    "Parker",
    "Quinn",
    "Reese",
    "Bailey",
    "Emerson",
    "Hayden",
    "Rowan",
    "Sage",
    "Charlie",
    "Finley",
    "Dakota",
    "Robin",
    "Blake",
]


COURSES = [
    "Applied Artificial Intelligence",
    "Accountancy",
    "Digital Supply Chain",
    "Mechanical Engineering",
    "Computing Science",
    "Computer Engineering",
    "Aviation Management",
    "Robotics Systems",
]


HOBBIES = [
    ["Anime", "Gaming"],
    ["Gym", "Running"],
    ["Music", "Cafe hopping"],
    ["Travel", "Photography"],
    ["Coding", "Technology"],
    ["Badminton", "Sports"],
    ["Movies", "Reading"],
    ["Cooking", "Food"],
]


MBTI_TYPES = [
    "ENFP",
    "ISFJ",
    "ESTP",
    "ISTP",
    "INTP",
    "ENFJ",
    "ISTJ",
    "ENTP",
]


FAKE_IDS = []


for index in range(25):

    student_id = str(9000002 + index)

    FAKE_IDS.append(student_id)

    name = NAMES[index]

    hobbies = HOBBIES[
        index % len(HOBBIES)
    ]

    PROFILES[student_id] = {

        "student_id":
            student_id,

        "name":
            name,

        "birthday":
            "01/01/2005",

        "gender":
            "Female"
            if index % 2 == 0
            else "Male",

        "year":
            str((index % 4) + 1),

        "course":
            COURSES[
                index % len(COURSES)
            ],

        "bio":
            f"Hi, I'm {name}. "
            f"I enjoy {hobbies[0].lower()} "
            f"and meeting new people.",

        "religion":
            None,

        "mbti":
            MBTI_TYPES[
                index % len(MBTI_TYPES)
            ],

        "match_preference":
            "Both",

        "here_for":
            "Both"
            if index % 3 == 0
            else "Friends",

        "expectations":
            (
                "Looking to meet someone "
                "with similar interests."
                if index % 3 == 0
                else None
            ),

        "telegram_handle":
            f"@{name.lower()}_test",

        "insta_handle":
            f"@{name.lower()}_test",

        "ccas":
            ["Sports Club"]
            if index % 4 == 0
            else [],

        "events":
            ["SIT Orientation"]
            if index % 3 == 0
            else [],

        "hobbies":
            hobbies,

        "interest_groups":
            ["Technology"]
            if index % 5 == 0
            else [],

        "profile_complete":
            True,
    }


# ============================================================
# HARDCODED AI RESPONSES
# ============================================================

AI_SCORES = {}


for index, student_id in enumerate(
    FAKE_IDS
):

    AI_SCORES[
        student_id
    ] = max(
        98 - index * 2,
        50
    )


# ============================================================
# FAKE MATCH STORAGE
# ============================================================

RECOMMENDATIONS = {
    TEST_USER: {}
}


ACCEPTED = {
    TEST_USER: []
}


REJECTED = {
    TEST_USER: []
}


for student_id in FAKE_IDS:

    ACCEPTED[
        student_id
    ] = []

    REJECTED[
        student_id
    ] = []


# ============================================================
# EVERY OTHER STUDENT HAS ALREADY DECIDED
#
# Alex -> ACCEPT
# Jamie -> REJECT
# Taylor -> ACCEPT
# Morgan -> REJECT
# ...
# ============================================================

OTHER_DECISIONS = {}


for index, student_id in enumerate(
    FAKE_IDS
):

    if index % 2 == 0:

        OTHER_DECISIONS[
            student_id
        ] = "accept"

        ACCEPTED[
            student_id
        ].append(
            TEST_USER
        )

    else:

        OTHER_DECISIONS[
            student_id
        ] = "reject"

        REJECTED[
            student_id
        ].append(
            TEST_USER
        )


# ============================================================
# FAKE DATABASE FUNCTIONS
# ============================================================

def fake_get_profile(
    student_id
):

    return PROFILES.get(
        str(student_id)
    )


def fake_read_profile(
    student_id,
    sheet_name="users"
):

    student_id = str(
        student_id
    )

    if sheet_name == "matches":

        return {

            "student_id":
                student_id,

            "recco_student_id":
                RECOMMENDATIONS.get(
                    student_id,
                    {}
                ),

            "accepted_student_id":
                ACCEPTED.get(
                    student_id,
                    []
                ),

            "rejected_student_id":
                REJECTED.get(
                    student_id,
                    []
                ),
        }

    return PROFILES.get(
        student_id
    )


def fake_save_profile(
    profile,
    partial=False
):

    student_id = str(
        profile["student_id"]
    )

    if student_id not in PROFILES:

        PROFILES[
            student_id
        ] = {}

    PROFILES[
        student_id
    ].update(
        profile
    )

    PROFILES[
        student_id
    ][
        "profile_complete"
    ] = True

    return {
        "saved": True,
        "message":
            "Profile saved successfully."
    }


def fake_delete_user(
    student_id
):

    student_id = str(
        student_id
    )

    PROFILES.pop(
        student_id,
        None
    )

    RECOMMENDATIONS.pop(
        student_id,
        None
    )

    ACCEPTED.pop(
        student_id,
        None
    )

    REJECTED.pop(
        student_id,
        None
    )

    return 200


def fake_get_user_recco_student_id(
    student_id
):

    return {

        "success":
            True,

        "error":
            None,

        "recco_student_id":
            RECOMMENDATIONS.get(
                str(student_id),
                {}
            )
    }


# ============================================================
# FAKE AUTHENTICATION
# ============================================================

def fake_is_valid_student_id(
    student_id
):

    student_id = str(
        student_id
    )

    return (
        len(student_id) == 7
        and student_id.isdigit()
    )


async def fake_login_user(
    student_id
):

    print(
        "OTP sent successfully."
    )

    print(
        "Sample OTP:",
        TEST_OTP
    )

    return 200


def fake_validate_otp(
    student_id,
    otp
):

    if otp == TEST_OTP:

        return 200

    return 403


# ============================================================
# FAKE MATCHES.PY DATABASE WRAPPERS
#
# matching_logic.py will use these.
# ============================================================

def fake_get_recco_student_id(
    student_id
):

    return {

        "success":
            True,

        "recco_student_id":
            RECOMMENDATIONS.get(
                str(student_id),
                {}
            )
    }


def fake_get_accepted_match(
    student_id
):

    return {

        "success":
            True,

        "accepted_student_id":
            ACCEPTED.get(
                str(student_id),
                []
            )
    }


def fake_get_rejected_match(
    student_id
):

    return {

        "success":
            True,

        "rejected_student_id":
            REJECTED.get(
                str(student_id),
                []
            )
    }


def fake_add_accepted_match(
    student_id,
    new_matches
):

    student_id = str(
        student_id
    )

    ACCEPTED.setdefault(
        student_id,
        []
    )

    for target_id in new_matches:

        target_id = str(
            target_id
        )

        if target_id not in ACCEPTED[
            student_id
        ]:

            ACCEPTED[
                student_id
            ].append(
                target_id
            )

    return {
        "success": True,
        "status": 200
    }


def fake_remove_accepted_match(
    student_id,
    matches_to_remove
):

    student_id = str(
        student_id
    )

    for target_id in matches_to_remove:

        target_id = str(
            target_id
        )

        if target_id in ACCEPTED.get(
            student_id,
            []
        ):

            ACCEPTED[
                student_id
            ].remove(
                target_id
            )

    return {
        "success": True,
        "status": 200
    }


def fake_add_rejected_match(
    student_id,
    new_matches
):

    student_id = str(
        student_id
    )

    REJECTED.setdefault(
        student_id,
        []
    )

    for target_id in new_matches:

        target_id = str(
            target_id
        )

        if target_id not in REJECTED[
            student_id
        ]:

            REJECTED[
                student_id
            ].append(
                target_id
            )

    return {
        "success": True,
        "status": 200
    }


def fake_remove_recco_student_id(
    student_id,
    students_to_remove
):

    student_id = str(
        student_id
    )

    RECOMMENDATIONS.setdefault(
        student_id,
        {}
    )

    for target_id in students_to_remove:

        RECOMMENDATIONS[
            student_id
        ].pop(
            str(target_id),
            None
        )

    return {
        "success": True,
        "status": 200
    }


# ============================================================
# FAKE PROFILE-MATCHING AI
# ============================================================

class FakeGroqClient:

    def close(self):

        pass


def fake_get_groq_client():

    return FakeGroqClient()


def fake_ai_profile_matching(
    student_id,
    client
):

    results = []


    for (
        target_id,
        score
    ) in AI_SCORES.items():

        profile = (
            PROFILES[
                target_id
            ]
        )

        results.append({

            "user_id":
                target_id,

            "name":
                profile["name"],

            "score":
                score,
        })


    return results


def fake_add_to_database(
    student_id,
    recommendations
):

    RECOMMENDATIONS[
        str(student_id)
    ] = {

        str(
            result["user_id"]
        ):
            result["score"]

        for result in recommendations
    }

    return 200


# ============================================================
# FAKE POST-MATCH AI RESPONSE
# ============================================================

def fake_prepare_connection(
    profile_a,
    profile_b
):

    common = []


    for hobby in profile_a.get(
        "hobbies",
        []
    ):

        if hobby in profile_b.get(
            "hobbies",
            []
        ):

            common.append(
                f"You both enjoy {hobby}"
            )


    if not common:

        common = [
            "You are both interested "
            "in meeting new people"
        ]


    return {

        "success":
            True,

        "user_a":
            profile_a["student_id"],

        "user_b":
            profile_b["student_id"],


        "user_a_info": {

            "student_id":
                profile_a["student_id"],

            "name":
                profile_a["name"],

            "telegram_handle":
                profile_a.get(
                    "telegram_handle"
                ),

            "insta_handle":
                profile_a.get(
                    "insta_handle"
                ),
        },


        "user_b_info": {

            "student_id":
                profile_b["student_id"],

            "name":
                profile_b["name"],

            "telegram_handle":
                profile_b.get(
                    "telegram_handle"
                ),

            "insta_handle":
                profile_b.get(
                    "insta_handle"
                ),
        },


        "common_interests":
            common,


        "conversation_starters": [
            "What do you normally do after class?",
            "What is your favourite hobby?",
            "Which SIT event have you enjoyed most?",
        ],


        "outing_ideas": [
            "Have lunch together on campus",
            "Attend an SIT event together",
            "Study together between classes",
        ],
    }


def fake_format_recommendations(
    result,
    for_user="a"
):

    if not result.get(
        "success"
    ):

        return (
            "Could not generate "
            "suggestions."
        )


    if for_user == "a":

        other = result[
            "user_b_info"
        ]

    else:

        other = result[
            "user_a_info"
        ]


    lines = [

        "",

        "====================================",

        f"Connected with {other['name']}",

        "====================================",

        "",

        "Contact details released:",

        f"Telegram: "
        f"{other.get('telegram_handle')}",

        f"Instagram: "
        f"{other.get('insta_handle')}",

        "",

        "Things you have in common:",
    ]


    for item in result[
        "common_interests"
    ]:

        lines.append(
            f"- {item}"
        )


    lines.append("")

    lines.append(
        "Conversation starters:"
    )


    for item in result[
        "conversation_starters"
    ]:

        lines.append(
            f"- {item}"
        )


    lines.append("")

    lines.append(
        "Outing ideas:"
    )


    for item in result[
        "outing_ideas"
    ]:

        lines.append(
            f"- {item}"
        )


    return "\n".join(
        lines
    )


async def fake_get_matches_for_user_async(
    user_id
):

    user_id = str(
        user_id
    )

    connections = []


    for target_id in ACCEPTED.get(
        user_id,
        []
    ):


        # Only display MUTUAL matches
        if (
            user_id
            not in ACCEPTED.get(
                target_id,
                []
            )
        ):

            continue


        yours = PROFILES.get(
            user_id
        )

        theirs = PROFILES.get(
            target_id
        )


        if not yours or not theirs:

            continue


        connections.append(
            fake_prepare_connection(
                yours,
                theirs
            )
        )


    return connections


# ============================================================
# SHOW OTHER USER'S DECISION
#
# Uses REAL get_next_user() underneath.
# ============================================================

REAL_GET_NEXT_USER = (
    matching_logic.get_next_user
)


CURRENT_TARGET = {
    "student_id": None
}


def test_get_next_user(
    student_id
):

    result = REAL_GET_NEXT_USER(
        student_id
    )


    if result.get(
        "success"
    ):

        CURRENT_TARGET[
            "student_id"
        ] = str(
            result["student_id"]
        )


    return result


# ============================================================
# SHOW ACCEPTED / REJECTED UNDER RECOMMENDED PROFILE
# ============================================================

REAL_COMPATIBILITY_LABEL = (
    matching_logic.compatibility_label
)


def test_compatibility_label(
    score
):

    target_id = CURRENT_TARGET.get(
        "student_id"
    )


    if target_id:

        decision = OTHER_DECISIONS[
            target_id
        ]


        if decision == "accept":

            print(
                "Other student's decision: "
                "ACCEPTED YOU"
            )

        else:

            print(
                "Other student's decision: "
                "REJECTED YOU"
            )


    return REAL_COMPATIBILITY_LABEL(
        score
    )


# ============================================================
# HANDLE OTHER USER ALREADY REJECTING
#
# Normal real logic's "waiting" means:
# other user has not accepted yet.
#
# In this test every other user has already decided,
# so if they already rejected, we stop the match.
# ============================================================

REAL_HANDLE_MATCH_DECISION = (
    matching_logic.handle_match_decision
)


def test_handle_match_decision(
    student_id,
    target_id,
    decision
):

    student_id = str(
        student_id
    )

    target_id = str(
        target_id
    )

    decision = str(
        decision
    ).strip().lower()


    other_decision = (
        OTHER_DECISIONS[
            target_id
        ]
    )


    # ========================================================
    # THEY REJECTED + YOU ACCEPT
    # ========================================================

    if (
        other_decision == "reject"
        and decision == "accept"
    ):

        # Still exercise REAL record_accept()
        result = (
            matching_logic.record_accept(
                student_id,
                target_id
            )
        )


        if not result.get(
            "success"
        ):

            return {

                "success":
                    False,

                "status":
                    "error",

                "matched":
                    False,

                "release_contact":
                    False,

                "error":
                    result.get(
                        "error"
                    )
            }


        print()

        print(
            "The other student already "
            "rejected you."
        )

        print(
            "No match was created."
        )

        print(
            "Contact details remain hidden."
        )

        print()


        return {

            "success":
                True,

            "status":
                "rejected_by_other",

            "matched":
                False,

            "release_contact":
                False
        }


    # ========================================================
    # ALL OTHER CASES USE REAL handle_match_decision()
    # ========================================================

    result = (
        REAL_HANDLE_MATCH_DECISION(
            student_id,
            target_id,
            decision
        )
    )


    # ========================================================
    # MUTUAL MATCH:
    # IMMEDIATELY RELEASE HANDLES
    # ========================================================

    if (
        result.get(
            "success"
        )
        and result.get(
            "matched"
        )
        and result.get(
            "release_contact"
        )
    ):

        other = PROFILES[
            target_id
        ]


        print()

        print(
            "Mutual match confirmed."
        )

        print(
            "Contact details released:"
        )

        print(
            "Telegram:",
            other.get(
                "telegram_handle"
            )
        )

        print(
            "Instagram:",
            other.get(
                "insta_handle"
            )
        )

        print()


    # ========================================================
    # THEY ACCEPTED BUT YOU REJECTED
    # ========================================================

    if (
        other_decision == "accept"
        and decision == "reject"
        and result.get("success")
    ):

        print(
            "The other student accepted you, "
            "but you rejected the profile."
        )

        print(
            "No contact details released."
        )


    return result


# ============================================================
# RUN REAL main.py WITH MOCKED EXTERNAL SERVICES
# ============================================================

def run_test():

    with ExitStack() as stack:

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                db,
                "get_profile",
                fake_get_profile
            )
        )

        stack.enter_context(
            patch.object(
                db,
                "read_profile",
                fake_read_profile
            )
        )

        stack.enter_context(
            patch.object(
                db,
                "save_profile",
                fake_save_profile
            )
        )

        stack.enter_context(
            patch.object(
                db,
                "delete_user",
                fake_delete_user
            )
        )

        stack.enter_context(
            patch.object(
                db,
                "get_user_recco_student_id",
                fake_get_user_recco_student_id
            )
        )


        # ----------------------------------------------------
        # AUTH
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                auth,
                "is_valid_student_id",
                fake_is_valid_student_id
            )
        )

        stack.enter_context(
            patch.object(
                auth,
                "login_user",
                fake_login_user
            )
        )

        stack.enter_context(
            patch.object(
                auth,
                "validate_otp",
                fake_validate_otp
            )
        )


        # ----------------------------------------------------
        # MATCH DATABASE WRAPPERS
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                matches,
                "get_recco_student_id",
                fake_get_recco_student_id
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "get_accepted_match",
                fake_get_accepted_match
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "get_rejected_match",
                fake_get_rejected_match
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "add_accepted_match",
                fake_add_accepted_match
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "remove_accepted_match",
                fake_remove_accepted_match
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "add_rejected_match",
                fake_add_rejected_match
            )
        )

        stack.enter_context(
            patch.object(
                matches,
                "remove_recco_student_id",
                fake_remove_recco_student_id
            )
        )


        # ----------------------------------------------------
        # PROFILE MATCHING AI
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                profile_matching_AI,
                "get_groq_client",
                fake_get_groq_client
            )
        )

        stack.enter_context(
            patch.object(
                profile_matching_AI,
                "AI_Profile_Matching",
                fake_ai_profile_matching
            )
        )

        stack.enter_context(
            patch.object(
                profile_matching_AI,
                "Add_To_Database",
                fake_add_to_database
            )
        )


        # ----------------------------------------------------
        # POST-MATCH AI
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                matchmaking_ai,
                "prepare_connection",
                fake_prepare_connection
            )
        )

        stack.enter_context(
            patch.object(
                matchmaking_ai,
                "format_recommendations",
                fake_format_recommendations
            )
        )

        stack.enter_context(
            patch.object(
                matchmaking_ai,
                "get_matches_for_user_async",
                fake_get_matches_for_user_async
            )
        )


        # ----------------------------------------------------
        # SMALL TEST WRAPPERS AROUND REAL MATCH LOGIC
        # ----------------------------------------------------

        stack.enter_context(
            patch.object(
                matching_logic,
                "get_next_user",
                test_get_next_user
            )
        )

        stack.enter_context(
            patch.object(
                matching_logic,
                "compatibility_label",
                test_compatibility_label
            )
        )

        stack.enter_context(
            patch.object(
                matching_logic,
                "handle_match_decision",
                test_handle_match_decision
            )
        )


        # ====================================================
        # RUN REAL main.py
        # ====================================================

        main.main()


# ============================================================
# START TEST
# ============================================================

if __name__ == "__main__":

    run_test()
    