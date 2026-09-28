"""Telegram adapter for the shared profile form. No API calls at import time."""
import asyncio
import os
import secrets
from pathlib import Path

import data_manager
import io_manager
import logic_manager
from profile_schema import PROFILE_FIELDS

STATE_KEY = "profile_setup"
OPTIONS_PER_PAGE = 8
DATA_PATH = os.environ.get("SITOGETHER_DATA", str(Path(__file__).resolve().parents[1] / "data" / "profiles.json"))


async def reply(update, text):
    # Large lists/long summaries must stay below Telegram's message limit.
    for offset in range(0, len(text), 3500):
        await update.effective_message.reply_text(text[offset:offset + 3500])


async def private_chat(update):
    if update.effective_chat.type != "private":
        await reply(update, "Please complete profile setup in a private chat with this bot.")
        return False
    return True


async def student_id_for(update):
    from database.db import get_bot_user
    user = await asyncio.to_thread(get_bot_user, update.effective_user.id)
    return str(user["student_id"]) if user else None


async def setup(update, context):
    if not await private_chat(update):
        return
    try:
        student_id = await student_id_for(update)
    except Exception:
        await reply(update, "Could not check your login. Please try /setup again later.")
        return
    if not student_id:
        await reply(update, "Log in first using /login <student_id>, then verify your /otp.")
        return
    context.user_data.pop("editing_field", None)
    context.user_data[STATE_KEY] = {"profile": {"student_id": student_id}, "index": 1,
                                   "session": secrets.token_hex(4)}
    await reply(update, "Profile setup: send one answer at a time. /skip skips optional questions; /cancel discards this draft. Saving will replace your profile fields; unrelated fields are kept.")
    await prompt_next(update, context)


def option_menu(state, field, page=0):
    """Keep callback payloads short and tied to one draft/question."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    prefix = f"form:{state['session']}:{state['index']}"
    options = field["options"]
    buttons = [InlineKeyboardButton(io_manager.profile_value(field["key"], option), callback_data=f"{prefix}:pick:{i}")
               for i, option in enumerate(options)
               if page * OPTIONS_PER_PAGE <= i < (page + 1) * OPTIONS_PER_PAGE]
    width = 1 if field["key"] == "course" else 2
    rows = [buttons[i:i + width] for i in range(0, len(buttons), width)]
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton("Previous", callback_data=f"{prefix}:page:{page - 1}"))
    if (page + 1) * OPTIONS_PER_PAGE < len(options):
        navigation.append(InlineKeyboardButton("Next", callback_data=f"{prefix}:page:{page + 1}"))
    if navigation:
        rows.append(navigation)
    if not field["required"]:
        rows.append([InlineKeyboardButton("Skip", callback_data=f"{prefix}:skip:0")])
    return InlineKeyboardMarkup(rows)


async def prompt_next(update, context, page=0, edit_menu=False):
    state = context.user_data[STATE_KEY]
    while state["index"] < len(PROFILE_FIELDS):
        field = PROFILE_FIELDS[state["index"]]
        if not logic_manager.should_skip_field(state["profile"], field):
            break
        state["profile"][field["key"]] = [] if field["kind"] == "list" else None
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
    lines = [field["question"]]
    if field.get("hint"):
        lines.append(field["hint"])
    if field["key"] == "course":
        lines.extend(f"{number}. {option}" for number, option in enumerate(field["options"], 1))
        lines.append(f"Reply with the course number (1-{len(field['options'])}).")
        await reply(update, "\n".join(lines))
        return
    if field["kind"] in ("choice", "mbti"):
        lines.append("Tap an option below.")
        if len(field["options"]) > OPTIONS_PER_PAGE:
            pages = (len(field["options"]) + OPTIONS_PER_PAGE - 1) // OPTIONS_PER_PAGE
            lines.append(f"Page {page + 1} of {pages}")
        menu = option_menu(state, field, page)
        if edit_menu:
            await update.callback_query.edit_message_text("\n".join(lines), reply_markup=menu)
        else:
            await update.effective_message.reply_text("\n".join(lines), reply_markup=menu)
        return
    if not field["required"]:
        lines.append("Optional: send /skip to leave blank.")
    await reply(update, "\n".join(lines))


async def menu_choice(update, context):
    """Handle choices, paging and optional skips; reject old draft buttons."""
    query = update.callback_query
    state = context.user_data.get(STATE_KEY)
    try:
        prefix, session, index, action, selection = query.data.split(":")
        index, selection = int(index), int(selection)
    except (ValueError, AttributeError):
        await query.answer("This option is unavailable.")
        return
    if (update.effective_chat.type != "private" or not state or prefix != "form"
            or session != state.get("session") or index != state["index"]
            or not 0 <= index < len(PROFILE_FIELDS)):
        await query.answer("Use the latest question, or send /setup to start again.")
        return
    field = PROFILE_FIELDS[index]
    options = field.get("options", [])
    if action == "page" and 0 <= selection * OPTIONS_PER_PAGE < len(options):
        await query.answer()
        await prompt_next(update, context, page=selection, edit_menu=True)
        return
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
    if not await private_chat(update):
        return
    state = context.user_data.get(STATE_KEY)
    if not state:
        await reply(update, "Use /setup to begin your profile.")
        return
    if state["index"] >= len(PROFILE_FIELDS):
        await reply(update, "Your draft is ready. Send /save, /setup, or /cancel.")
        return
    field = PROFILE_FIELDS[state["index"]]
    value, error = io_manager.validate_field(update.effective_message.text if raw is None else raw, field)
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
    if not await private_chat(update):
        return
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
    profiles = data_manager.load_profiles(DATA_PATH)
    existing = data_manager.find_profile(profiles, student_id) or {}
    merged = {**existing, **profile}
    if not data_manager.save_profiles(DATA_PATH, data_manager.upsert_profile(profiles, merged)):
        await reply(update, "Save failed. Your draft is kept; retry /save.")
        return
    synced, message = await asyncio.to_thread(data_manager.sync_profile_to_sheets, merged)
    if synced:
        await reply(update, "Profile saved.")
        context.user_data.pop(STATE_KEY, None)
        await reply(update, "Use /profile to view your saved profile.")
    else:
        await reply(update, "Your profile was saved locally, but the online update failed. " + message)
        await reply(update, "Your draft is kept. Send /save to retry syncing.")
