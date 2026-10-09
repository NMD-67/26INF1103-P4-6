"""Telegram adapter for the shared profile form. No API calls at import time."""
import asyncio
import secrets

from database import db
import io_manager
import logic_manager
from profile_schema import PROFILE_FIELDS

STATE_KEY = "profile_setup"


def uses_buttons(field):
    if field["key"] == "course":
        return False
    return field["kind"] in ("choice", "mbti")


def question_lines(field):
    lines = [field["question"]]
    if field.get("hint"):
        lines.append(field["hint"])
    if field["key"] == "course":
        for number, option in enumerate(field["options"], start=1):
            lines.append(f"{number}. {option}")
        lines.append(f"Reply with the course number (1-{len(field['options'])}).")
    return lines


def option_rows(field, prefix, width=2):
    """Build rows containing every option."""
    from telegram import InlineKeyboardButton
    options = field["options"]
    buttons = []
    for index in range(len(options)):
        label = io_manager.profile_value(field["key"], options[index])
        buttons.append(InlineKeyboardButton(label, callback_data=f"{prefix}:{index}"))
    rows = []
    for index in range(0, len(buttons), width):
        rows.append(buttons[index:index + width])
    return rows


async def reply(update, text):
    # Large lists/long summaries must stay below Telegram's message limit.
    for offset in range(0, len(text), 3500):
        await update.effective_message.reply_text(text[offset:offset + 3500])


async def student_id_for(update):
    from database.db import get_bot_user
    user = await asyncio.to_thread(get_bot_user, update.effective_user.id)
    if user is None:
        return None
    return str(user["student_id"])


async def setup(update, context):
    try:
        student_id = await student_id_for(update)
    except Exception:
        await reply(update, "Could not check your login. Please try /setup again later.")
        return
    if not student_id:
        await reply(update, "Log in first using /login <student_id>, then verify your /otp.")
        return
    context.user_data.pop("editing_field", None)
    # Telegram keeps a separate user_data dictionary for each person.
    context.user_data[STATE_KEY] = {
        "profile": {"student_id": student_id},
        "index": 1,  # Student ID is already known, so begin with the name question.
        "session": secrets.token_hex(4),  # Identifies buttons from this setup attempt.
    }
    await reply(update, "Profile setup: send one answer at a time. /skip skips optional questions; /cancel discards this draft. Saving will replace your profile fields; unrelated fields are kept.")
    await prompt_next(update, context)


def option_menu(state, field):
    """Keep callback payloads short and tied to one draft/question."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    prefix = f"form:{state['session']}:{state['index']}"
    rows = option_rows(field, f"{prefix}:pick")
    if not field["required"]:
        rows.append([InlineKeyboardButton("Skip", callback_data=f"{prefix}:skip:0")])
    return InlineKeyboardMarkup(rows)


async def prompt_next(update, context):
    state = context.user_data[STATE_KEY]
    while state["index"] < len(PROFILE_FIELDS):
        field = PROFILE_FIELDS[state["index"]]
        if not logic_manager.should_skip_field(state["profile"], field):
            break
        if field["kind"] == "list":
            state["profile"][field["key"]] = []
        else:
            state["profile"][field["key"]] = None
        state["index"] += 1
    if state["index"] == len(PROFILE_FIELDS):
        profile = state["profile"]
        profile["traits"] = logic_manager.derive_profile_traits(profile)
        profile["profile_complete"] = logic_manager.is_profile_complete(profile, PROFILE_FIELDS)
        lines = ["Review your profile:"]
        for field in PROFILE_FIELDS:
            key = field["key"]
            lines.append(f"{io_manager.profile_label(key)}: {io_manager.profile_value(key, profile.get(key))}")
        lines.append("Send /save to save, /setup to start again, or /cancel to discard.")
        await reply(update, "\n".join(lines))
        return
    lines = question_lines(field)
    if uses_buttons(field):
        if field["key"] != "gender":
            lines.append("Tap an option below.")
        menu = option_menu(state, field)
        await update.effective_message.reply_text("\n".join(lines), reply_markup=menu)
        return
    if not field["required"]:
        lines.append("Optional: send /skip to leave blank.")
    await reply(update, "\n".join(lines))


async def menu_choice(update, context):
    """Handle choices and optional skips; reject old draft buttons."""
    query = update.callback_query
    state = context.user_data.get(STATE_KEY)
    try:
        prefix, session, index, action, selection = query.data.split(":")
        index, selection = int(index), int(selection)
    except (ValueError, AttributeError):
        await query.answer("This option is unavailable.")
        return
    # Check the chat, then the draft, then the question. Old buttons must not
    # answer a different question after the user has moved on.
    unavailable = "Use the latest question, or send /setup to start again."
    if not state:
        await query.answer(unavailable)
        return
    if prefix != "form" or session != state.get("session"):
        await query.answer(unavailable)
        return
    if index != state["index"] or not 0 <= index < len(PROFILE_FIELDS):
        await query.answer(unavailable)
        return
    field = PROFILE_FIELDS[index]
    options = field.get("options", [])
    if action == "pick" and 0 <= selection < len(options):
        raw = options[selection]
    elif action == "skip" and not field["required"]:
        raw = ""
    else:
        await query.answer("Please select a valid option.")
        return
    await query.answer()
    await answer(update, context, raw=raw)
    # The answer is already recorded; a failed visual cleanup must not undo it.
    from telegram.error import TelegramError
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass


async def answer(update, context, raw=None):
    state = context.user_data.get(STATE_KEY)
    if not state:
        await reply(update, "Use /setup to begin your profile.")
        return
    if state["index"] >= len(PROFILE_FIELDS):
        await reply(update, "Your draft is ready. Send /save, /setup, or /cancel.")
        return
    field = PROFILE_FIELDS[state["index"]]
    # A button supplies raw; a typed answer comes from the message text.
    if raw is None:
        raw = update.effective_message.text
    value, error = io_manager.validate_field(raw, field)
    if error:
        await reply(update, error)
        return
    state["profile"][field["key"]] = value
    state["index"] += 1
    await prompt_next(update, context)


async def skip(update, context):
    await answer(update, context, raw="")


async def cancel(update, context):
    context.user_data.pop(STATE_KEY, None)
    context.user_data.pop("editing_field", None)
    await reply(update, "Draft cancelled. Previously saved profiles are unchanged.")


async def save(update, context):
    state = context.user_data.get(STATE_KEY)
    if not state or state["index"] != len(PROFILE_FIELDS):
        await reply(update, "Complete /setup before saving.")
        return
    try:
        student_id = await student_id_for(update)
    except Exception:
        await reply(update, "Could not check your login. Your draft is kept; retry /save.")
        return
    if student_id != state["profile"]["student_id"]:
        await reply(update, "Your login changed. Please log in and start /setup again.")
        return
    profile = state["profile"]
    # Saving uses the network; to_thread lets the bot keep responding meanwhile.
    result = await asyncio.to_thread(db.save_profile, profile)
    if result["saved"]:
        await reply(update, "Profile saved.")
        context.user_data.pop(STATE_KEY, None)
        await reply(update, "Use /profile to view your saved profile.")
    else:
        await reply(update, result["message"])
        await reply(update, "Your draft is kept in this running bot. Send /save to retry. It will be lost if the bot restarts.")
