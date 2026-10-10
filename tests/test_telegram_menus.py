"""Offline inline-button checks: py tests/test_telegram_menus.py."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import io_manager
from tele import profile_setup as form


def fixture(key):
    index = next(i for i, field in enumerate(form.PROFILE_FIELDS) if field["key"] == key)
    state = {"profile": {"student_id": "0123456"}, "index": index, "session": "test1234"}
    query = SimpleNamespace(data="", answer=AsyncMock(), edit_message_text=AsyncMock(),
                            edit_message_reply_markup=AsyncMock())
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(type="private"),
                             effective_message=SimpleNamespace(reply_text=AsyncMock()))
    return update, SimpleNamespace(user_data={form.STATE_KEY: state}), state


async def run_checks():
    update, context, state = fixture("gender")
    field = form.PROFILE_FIELDS[state["index"]]
    keyboard = form.option_menu(state, field)
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert [button.text for button in buttons] == ["Male", "Female", "Other"]
    update.callback_query.data = buttons[1].callback_data
    await form.menu_choice(update, context)
    assert state["profile"]["gender"] == "Female"
    next_index = state["index"]
    await form.menu_choice(update, context)  # double tap must not answer the next question
    assert state["index"] == next_index

    update, context, state = fixture("course")
    await form.prompt_next(update, context)
    prompt = "\n".join(call.args[0] for call in update.effective_message.reply_text.call_args_list)
    assert "1. Accountancy" in prompt and "Reply with the course number" in prompt
    assert all("reply_markup" not in call.kwargs for call in update.effective_message.reply_text.call_args_list)
    await form.answer(update, context, raw="3")
    assert state["profile"]["course"] == "Applied Artificial Intelligence"

    update, context, state = fixture("religion")
    field = form.PROFILE_FIELDS[state["index"]]
    keyboard = form.option_menu(state, field)
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert [button.text for button in buttons] == field["options"] + ["Skip"]
    assert all(len(button.callback_data.encode()) <= 64 for button in buttons)
    # An old pagination button must not change the current answer.
    update.callback_query.data = f"form:test1234:{state['index']}:page:1"
    await form.menu_choice(update, context)
    assert "religion" not in state["profile"]
    update.callback_query.edit_message_text.assert_not_awaited()
    update.callback_query.data = f"form:test1234:{state['index']}:pick:8"
    await form.menu_choice(update, context)
    assert state["profile"]["religion"] == field["options"][8]

    update, context, state = fixture("mbti")
    await form.prompt_next(update, context)
    call = update.effective_message.reply_text.call_args
    buttons = [button for row in call.kwargs["reply_markup"].inline_keyboard for button in row]
    assert [button.text for button in buttons] == form.PROFILE_FIELDS[state["index"]]["options"] + ["Skip"]
    assert "Page " not in call.args[0]
    update.callback_query.data = f"form:test1234:{state['index']}:skip:0"
    await form.menu_choice(update, context)
    assert state["profile"]["mbti"] is None
    update, context, state = fixture("mbti")
    update.callback_query.data = f"form:test1234:{state['index']}:pick:0"
    await form.menu_choice(update, context)
    assert state["profile"]["mbti"] == "INTJ"

    update, context, state = fixture("gender")
    index = state["index"]
    for payload in [f"form:old:{index}:pick:0", f"form:test1234:{index}:skip:0",
                    f"form:test1234:{index}:pick:999", "form:broken"]:
        update.callback_query.data = payload
        await form.menu_choice(update, context)
        assert state["index"] == index and "gender" not in state["profile"]


if __name__ == "__main__":
    asyncio.run(run_checks())
    io_manager.show("Telegram menu checks passed (no live API calls).")
