"""Offline validation checks: py tests/test_telegram_edits.py."""
import asyncio
import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import io_manager

# Stub service modules before importing bot.py: never read credentials or contact APIs.
db = ModuleType("database.db")
db.save_user = Mock()
db.get_bot_user = Mock(return_value={"student_id": "0123456"})
auth = ModuleType("src.auth")
auth.login_user = AsyncMock()
auth.validate_otp = Mock()
auth.get_user_info = Mock()
save_profile = Mock(return_value={"saved": True})
db.save_profile = save_profile
dotenv = ModuleType("dotenv")
dotenv.load_dotenv = Mock()
with patch.dict(sys.modules, {"database.db": db, "src.auth": auth, "dotenv": dotenv}):
    bot = importlib.import_module("tele.bot")


def fixture(key, text):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    update = SimpleNamespace(message=message, effective_message=message,
                             effective_chat=SimpleNamespace(type="private"),
                             effective_user=SimpleNamespace(id=123))
    return update, SimpleNamespace(user_data={"editing_field": "edit_" + key})


async def run_checks():
    invalid = {
        "insta_handle": "https://instagram.com/example",
        "name": "123", "birthday": "31/02/2004", "gender": "unknown",
        "year": "5", "course": "999", "bio": "a" * 301,
        "religion": "invalid", "mbti": "ABCD", "match_preference": "invalid",
        "here_for": "invalid", "expectations": "short", "telegram_handle": "@ab",
        "ccas": "a" * 41, "events": "a" * 41, "hobbies": " , ",
        "interest_groups": "a" * 41,
    }
    assert set(invalid) == set(bot.USER_PROFILE_HANDLERS)
    for key, text in invalid.items():
        save_profile.reset_mock()
        update, context = fixture(key, text)
        await bot.text_handler(update, context)
        save_profile.assert_not_called()
        assert context.user_data["editing_field"] == "edit_" + key
        assert "Please try again" in update.message.reply_text.call_args.args[0]

    # Range checking, required blanks, canonical values, and list serialization.
    for key, text in [("birthday", "01/01/2099"), ("name", " ")]:
        save_profile.reset_mock()
        update, context = fixture(key, text)
        await bot.text_handler(update, context)
        save_profile.assert_not_called()
    for key, text, expected in [
        ("insta_handle", "Example.User", "@example.user"),
        ("insta_handle", "@example_user", "@example_user"),
        ("insta_handle", " ", None),
        ("mbti", "intj", "INTJ"), ("course", "3", "Applied Artificial Intelligence"),
        ("hobbies", "Reading, reading, Swimming", ["Reading", "Swimming"]),
        ("ccas", "Music, music", ["Music"]), ("gender", "female", "Female"),
        ("bio", " ", None), ("telegram_handle", "example_user", "@example_user"),
    ]:
        save_profile.reset_mock()
        update, context = fixture(key, text)
        await bot.text_handler(update, context)
        save_profile.assert_called_once_with({"student_id": "0123456", key: expected}, partial=True)
        assert "editing_field" not in context.user_data

    # Required fields retain the edit after a failure; auth is rechecked before writes.
    update, context = fixture("name", "Test Student")
    db.get_bot_user.return_value = None
    save_profile.reset_mock()
    await bot.text_handler(update, context)
    save_profile.assert_not_called()
    db.get_bot_user.return_value = {"student_id": "0123456"}
    save_profile.return_value = {"saved": False, "message": "Failed"}
    update, context = fixture("name", "Test Student")
    await bot.text_handler(update, context)
    assert context.user_data["editing_field"] == "edit_name"
    save_profile.side_effect = RuntimeError("Unavailable")
    await bot.text_handler(update, context)
    assert context.user_data["editing_field"] == "edit_name"
    save_profile.side_effect = None

    # Edit prompts are sourced from the schema and expose numbered course choices.
    update, context = fixture("course", "")
    update.callback_query = SimpleNamespace(data="edit_course", answer=AsyncMock(), message=update.message)
    await bot.edit_profile_button_handler(update, context)
    assert "1. Accountancy" in update.message.reply_text.call_args.args[0]
    assert "Which course are you studying?" in update.message.reply_text.call_args.args[0]
    assert "reply_markup" not in update.message.reply_text.call_args.kwargs

    save_profile.return_value = {"saved": True}
    # Exercise real callback shapes: Telegram callbacks have no update.message.
    for key, expected in [("gender", "Male"), ("year", "1"), ("religion", "Buddhism"),
                          ("mbti", "INTJ"), ("match_preference", "Male"), ("here_for", "Friends")]:
        update, context = fixture(key, "")
        message = update.message
        update.callback_query = SimpleNamespace(data=f"edit_{key}", answer=AsyncMock(),
                                                message=message, edit_message_reply_markup=AsyncMock())
        update.message = None
        await bot.edit_profile_button_handler(update, context)
        menu = message.reply_text.call_args.kwargs["reply_markup"]
        assert all(len(button.callback_data.encode()) <= 64 for row in menu.inline_keyboard for button in row)
        if key == "here_for":
            assert "Relationships and Friends" in [button.text for row in menu.inline_keyboard for button in row]
        update.callback_query.data = menu.inline_keyboard[0][0].callback_data
        save_profile.reset_mock()
        await bot.edit_option_handler(update, context)
        save_profile.assert_called_once_with({"student_id": "0123456", key: expected}, partial=True)
        assert "editing_field" not in context.user_data
        await bot.edit_option_handler(update, context)
        assert save_profile.call_count == 1, "Repeated taps must not write again"

    # An old menu for the same field cannot overwrite a later edit session.
    update, context = fixture("gender", "")
    context.user_data["editing_token"] = "newsession"
    update.callback_query = SimpleNamespace(data="editpick:oldsession:gender:0", answer=AsyncMock())
    save_profile.reset_mock()
    await bot.edit_option_handler(update, context)
    save_profile.assert_not_called()


if __name__ == "__main__":
    with patch.object(bot.db, "save_profile", save_profile):
        asyncio.run(run_checks())
    io_manager.show("Telegram edit checks passed (no credentials or live services used).")
