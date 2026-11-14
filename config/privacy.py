"""Shared user-facing privacy information for CLI and Telegram."""
BIO_PRIVACY_WARNING = (
    "Do not include email addresses, phone numbers, your student ID, home address, "
    "social media handles or other identifying details in your bio."
)

PRIVACY_NOTICE = (
    "SITogether privacy notice\n\n"
    "We use your student ID to verify your school account by email OTP. "
    "Profile information is stored in our project database to provide matching and connections.\n\n"
    "Selected profile details, including bio, interests and matching information, "
    "are sent to Groq to generate compatibility scores and conversation suggestions. "
    "Dedicated name, student ID, birthday and contact-handle fields are excluded from AI prompts; "
    "identifying details you put in free text may still be sent. "
    "External providers may process data outside Singapore.\n\n"
    "Other users can see profile details when browsing recommendations. "
    "Telegram and Instagram handles are shown in connections after mutual acceptance. "
    "Use Update profile to correct your details or Delete account to request account removal.\n\n"
    "Birthday input is used to calculate age and horoscope; the current profile-saving flow "
    "does not save the full birthday. Optional questions can be skipped.\n\n"
    + BIO_PRIVACY_WARNING + "\n\n"
    "If you do not want to provide your information, exit now before entering your student ID "
    "(Ctrl+C in the CLI, or /cancel in Telegram)."
)
