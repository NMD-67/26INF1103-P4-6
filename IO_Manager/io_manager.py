"""Compatibility exports for older callers. Main uses ConsoleIO directly."""
from config.user_fields import PROFILE_FIELDS
from IO_Manager.console_io import ConsoleIO
from IO_Manager.profile_validator import ProfileValidator

_console = ConsoleIO()
_validator = ProfileValidator()
MIN_AGE = ProfileValidator.MIN_AGE
MAX_AGE = ProfileValidator.MAX_AGE
MAX_LIST_ITEMS = ProfileValidator.MAX_LIST_ITEMS
MAX_ITEM_LEN = ProfileValidator.MAX_ITEM_LEN
LETTERS = ProfileValidator.LETTERS
DIGITS = ProfileValidator.DIGITS

show = _console.show
show_error = _console.show_error
show_section = _console.show_section
_show_options = _console._show_options
ask_field = _console.ask_field
ask_profile_field = _console.ask_profile_field
collect_profile = _console.collect_profile
collect_missing = _console.collect_missing
confirm = _console.confirm
profile_label = _console.profile_label
profile_value = _console.profile_value
_format_value = _console._format_value
show_profile_summary = _console.show_profile_summary
validate_field = _console.validate_field
_validate_student_id = _validator._validate_student_id
_validate_name = _validator._validate_name
_validate_date = _validator._validate_date
_validate_choice = _validator._validate_choice
_validate_mbti = _validator._validate_mbti
_validate_text = _validator._validate_text
_validate_telegram = _validator._validate_telegram
_validate_instagram = _validator._validate_instagram
_validate_list = _validator._validate_list
_validate_age = _validator._validate_age
