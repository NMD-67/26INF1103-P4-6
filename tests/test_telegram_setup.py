"""Offline Telegram form checks: py tests/test_telegram_setup.py."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import io_manager
from tele import profile_setup as form


def make_update(chat_type="private"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(type=chat_type),
        effective_user=SimpleNamespace(id=123),
        effective_message=SimpleNamespace(text="", reply_text=AsyncMock()),
    )


async def run_checks():
    update = make_update()
    context = SimpleNamespace(user_data={})
    with patch.object(form, "student_id_for", new=AsyncMock(return_value=None)):
        await form.setup(update, context)
        assert form.STATE_KEY not in context.user_data
    with patch.object(form, "student_id_for", new=AsyncMock(return_value="0123456")) as identity:
        await form.setup(make_update("group"), context)
        identity.assert_not_called()
        await form.setup(update, context)
        assert context.user_data[form.STATE_KEY]["profile"] == {"student_id": "0123456"}
        await form.skip(update, context)
        assert context.user_data[form.STATE_KEY]["index"] == 1
        update.effective_message.text = "1"
        await form.answer(update, context)
        assert context.user_data[form.STATE_KEY]["index"] == 1

        # Incomplete drafts must never save or contact the sync service.
        with patch.object(form.db, "sync_profile_to_sheets") as sync:
            await form.save(update, context)
            sync.assert_not_called()

        answers = {
            "name": "Test Student", "birthday": "01/01/2004", "gender": "1",
            "year": "1", "course": "1", "match_preference": "Both",
            "here_for": "Friends", "telegram_handle": "@example_user",
            "hobbies": "Reading, reading, Swimming",
        }
        while context.user_data[form.STATE_KEY]["index"] < len(form.PROFILE_FIELDS):
            state = context.user_data[form.STATE_KEY]
            field = form.PROFILE_FIELDS[state["index"]]
            assert field["key"] != "expectations", "Friends must skip relationship expectations"
            if field["key"] in answers:
                update.effective_message.text = answers[field["key"]]
                await form.answer(update, context)
            else:
                await form.skip(update, context)
        draft = context.user_data[form.STATE_KEY]["profile"]
        assert draft["profile_complete"] and draft["traits"]["western_zodiac"] == "Capricorn"
        assert draft["hobbies"] == ["Reading", "Swimming"]
        assert draft["ccas"] == [] and draft["expectations"] is None
        assert all(len(call.args[0]) <= 3500 for call in update.effective_message.reply_text.call_args_list)

        # A second user's draft is independent.
        second_context = SimpleNamespace(user_data={})
        await form.setup(update, second_context)
        assert context.user_data[form.STATE_KEY]["index"] == len(form.PROFILE_FIELDS)
        await form.cancel(update, second_context)
        assert form.STATE_KEY not in second_context.user_data

        with patch.object(form, "student_id_for", new=AsyncMock(return_value="9999999")), patch.object(form.db, "sync_profile_to_sheets") as sync:
            await form.save(update, context)
            sync.assert_not_called()
        with patch.object(form.db, "sync_profile_to_sheets", return_value=(False, "Offline")):
            await form.save(update, context)
            assert form.STATE_KEY in context.user_data
            assert context.user_data[form.STATE_KEY]["profile"] == draft
            assert "retry" in update.effective_message.reply_text.call_args.args[0]
        with patch.object(form.db, "sync_profile_to_sheets", return_value=(True, "Saved")) as sync:
            await form.save(update, context)
            sync.assert_called_once_with(draft, partial=False)
            assert form.STATE_KEY not in context.user_data


if __name__ == "__main__":
    asyncio.run(run_checks())
    io_manager.show("Telegram setup checks passed (no messages or live API calls sent).")
