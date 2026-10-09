"""Single source of truth for the SITogether profile form.

Pure data only: no logic, no printing. io_manager reads it to build prompts,
logic_manager reads it to decide which fields are required or skipped.
"""

SECTION_BACKGROUND = "Background Information"
SECTION_PERSONAL = "Personal Information"
SECTION_EXTRA = "Extracurricular"

RELIGIONS = [
    "Buddhism", "Christianity", "Catholicism", "Islam", "Hinduism",
    "Taoism", "Sikhism", "Free thinker", "No religion", "Others",
]

SIT_COURSES = [
    "Accountancy",
    "Aircraft Systems Engineering",
    "Applied Artificial Intelligence",
    "Applied Computing",
    "Applied Computing (Fintech)",
    "Applied Computing Degree (via CSM Pathway)",
    "Aviation Management",
    "Business and Infocomm Technology",
    "Chemical Engineering",
    "Civil Engineering",
    "Communication and Digital Media",
    "Computer Engineering",
    "Computer Science in Interactive Media and Game Development",
    "Computer Science in Real-Time Interactive Simulation",
    "Computing Science",
    "Diagnostic Radiography",
    "Dietetics and Nutrition",
    "Digital Supply Chain",
    "Electrical and Electronic Engineering",
    "Electrical and Electronic Engineering Degree (via CSM Pathway)",
    "Electrical Power Engineering",
    "Electronics and Data Engineering",
    "Engineering Systems",
    "Food Business Management (Baking and Pastry Arts)",
    "Food Business Management (Culinary Arts)",
    "Food Technology",
    "Hospitality and Tourism Management",
    "Information and Communications Technology (Information Security)",
    "Information and Communications Technology (Software Engineering)",
    "Mechanical Design and Manufacturing Engineering",
    "Mechanical Engineering",
    "Naval Architecture and Marine Engineering",
    "Nursing",
    "Occupational Therapy",
    "Pharmaceutical Engineering",
    "Physiotherapy",
    "Physiotherapy (Top-Up)",
    "Radiation Therapy",
    "Robotics Systems",
    "Speech and Language Therapy",
    "Sustainable Built Environment",
    "User Experience and Game Design",
]

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
]

# kind decides which validator io_manager applies.
# skip_if (optional): {"field": <key already collected earlier>, "in": [<values>]}
# means logic_manager.should_skip_field() will tell io_manager not to ask this
# question at all when the referenced field already holds one of those values.
# Each dictionary describes one question. The list order is the question order.
# key: stored name; question/label: displayed text; section: question group.
# required: must be answered; kind: which validation function to use.
# options/hint/length limits add settings for individual questions.
PROFILE_FIELDS = [
    # Background Information
    {
        "key": "student_id",
        "question": "What is your student ID?",
        "label": "Student ID (your login)",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "student_id",
        "hint": "7 digits, e.g. 2500123",
    },

    {
        "key": "name",
        "question": "What is your name?",
        "label": "Name",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "name",
    },

    {
        "key": "birthday",
        "question": "When is your birthday?",
        "label": "Birthday",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "date",
        "hint": "DD/MM/YYYY",
    },

    {
        "key": "gender",
        "question": "What is your gender?",
        "label": "Gender",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": ["Male", "Female", "Other"],
    },

    {
        "key": "year",
        "question": "Which year of study are you in?",
        "label": "Year of study",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": ["1", "2", "3", "4"],
    },

    {
        "key": "course",
        "question": "Which course are you studying?",
        "label": "Course",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": SIT_COURSES,
    },

    {
        "key": "bio",
        "question": "What would you like others to know about you?",
        "label": "Bio",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "text",
        "min_len": 1,
        "max_len": 300,
        "hint": "max 300 characters; Tell us more about yourself",
    },

    {
        "key": "religion",
        "question": "What is your religion?",
        "label": "Religion",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "choice",
        "options": RELIGIONS,
    },

    {
        "key": "mbti",
        "question": "What is your MBTI personality type?",
        "label": "MBTI",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "mbti",
        "options": MBTI_TYPES,
        "hint": "e.g. INTJ",
    },

    # Personal Information
    {
        "key": "match_preference",
        "question": "Who would you like to be matched with?",
        "label": "Match me with",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "choice",
        "options": ["Male", "Female", "Both"],
    },

    {
        "key": "here_for",
        "question": "Are you here for friendship, a relationship, or both?",
        "label": "Here for",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "choice",
        "options": ["Friends", "Relationship", "Both"],
    },

    {
        "key": "expectations",
        "question": "What are you looking for in a relationship?",
        "label": "Expectations in relationships",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "text",
        "min_len": 10,
        "max_len": 500,
        "hint": "10-500 characters",
        "skip_if": {"field": "here_for", "in": ["Friends"]},
    },

    {
        "key": "telegram_handle",
        "question": "What is your Telegram handle?",
        "label": "Telegram handle",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "telegram",
        "hint": "only shared once you match",
    },

    {
        "key": "insta_handle",
        "question": "What is your Instagram handle?",
        "label": "Instagram Handle",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "instagram",
        "hint": "Username only, with or without @; optional",
    },

    # Extracurricular
    {
        "key": "ccas",
        "question": "Which CCAs are you currently involved in at SIT?",
        "label": "Current CCAs in SIT",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },

    {
        "key": "events",
        "question": "Which SIT events have you participated in?",
        "label": "Events joined in SIT",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },

    {
        "key": "hobbies",
        "question": "What are your hobbies?",
        "label": "Hobbies",
        "section": SECTION_EXTRA,
        "required": True,
        "kind": "list",
        "hint": "comma-separated, at least one",
    },

    {
        "key": "interest_groups",
        "question": "Which interest groups do you belong to outside SIT?",
        "label": "Outside interest groups",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },
]
