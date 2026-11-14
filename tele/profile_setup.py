"""Stateful Telegram profile draft; persistence uses the shared UserService."""
import asyncio
import logging
import secrets
from config.user_fields import PROFILE_FIELDS
from services.profile_form import ProfileForm

logger = logging.getLogger(__name__)
STATE_KEY = "profile_draft"


class TelegramProfileForm:
    def __init__(self, users, io, form=None):
        self._users = users
        self._io = io
        self._form = form if form is not None else ProfileForm()
        self._fields = {f["key"]: f for f in PROFILE_FIELDS if f["key"] != "student_id"}

    def state(self, update, context, student_id):
        state = context.user_data.get(STATE_KEY)
        if state and state["student_id"] == str(student_id) and state["chat_id"] == update.effective_chat.id:
            return state
        return None

    async def begin(self, update, context, student_id, editing=False):
        if STATE_KEY in context.user_data:
            await self._io.send(update, "A draft is already open. Use /save or /cancel in the chat where you started it.")
            return
        result = await asyncio.to_thread(self._users.get_profile, student_id)
        if not result.success:
            await self._io.send(update, result.error_msg)
            return
        answers = self._form.form_values(result.data)
        answers["student_id"] = str(student_id)
        fields = self._form.questions_for_profile(answers)
        pending = [] if editing else [f["key"] for f in fields
            if f["key"] != "student_id" and answers.get(f["key"]) in (None, "", [])]
        state = {"student_id": str(student_id), "chat_id": update.effective_chat.id,
                 "profile": answers, "pending": pending, "editing": editing,
                 "token": secrets.token_hex(4), "field": None, "phase": "fields"}
        context.user_data[STATE_KEY] = state
        await self._io.send(update, "Changes stay in a draft until you confirm Save. /cancel discards them. Drafts are lost if the bot restarts.")
        if editing:
            await self.edit_menu(update, state)
        else:
            await self.next_question(update, state)

    async def edit_menu(self, update, state):
        state["field"] = None
        state["phase"] = "fields"
        buttons = [(f["label"], f"field:{state['token']}:{key}") for key, f in self._fields.items()
                   if not self._form.should_skip(state["profile"], f)]
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows += [[("Review changes", f"draft:{state['token']}:review"),
                  ("Discard", f"draft:{state['token']}:cancel")]]
        await self._io.send(update, "Choose a field to update:", rows)

    async def next_question(self, update, state):
        while state["pending"]:
            key = state["pending"].pop(0)
            field = self._fields[key]
            if not self._form.should_skip(state["profile"], field):
                await self.prompt(update, state, key)
                return
        state["field"] = None
        if state["editing"]:
            await self.edit_menu(update, state)
        else:
            await self.review(update, state)

    async def prompt(self, update, state, key):
        field = self._fields[key]
        state.update(field=key, phase="question", revision=secrets.token_hex(3), selected=[])
        if field["kind"] == "multi_choice":
            saved = state["profile"].get(key) or []
            state["selected"] = [i for i, option in enumerate(field["options"]) if option in saved]
        await self.question(update, state)

    async def question(self, update, state):
        field = self._fields[state["field"]]
        lines = [field["question"]]
        if field.get("hint"):
            lines.append(field["hint"])
        rows = []
        prefix = f"answer:{state['token']}:{state['revision']}"
        if field["key"] == "course":
            lines.extend(f"{i}. {value}" for i, value in enumerate(field["options"], 1))
            lines.append("Reply with the course number.")
        elif field["kind"] in ("choice", "mbti", "multi_choice"):
            buttons = []
            for i, option in enumerate(field["options"]):
                label = ("✓ " if i in state["selected"] else "") + option
                buttons.append((label, f"{prefix}:{i}"))
            rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
            if field["kind"] == "multi_choice":
                lines.append("Select all that apply, then Done. You may also type comma-separated choices.")
                rows.append([("Done", f"{prefix}:done")])
        if not field["required"]:
            lines.append("Optional: /skip leaves this blank.")
            rows.append([("Skip", f"{prefix}:skip")])
        await self._io.send(update, "\n".join(lines), rows)

    async def answer(self, update, state, raw):
        if state["phase"] != "question" or not state.get("field"):
            await self._io.send(update, "Use the current buttons or /save to review your draft.")
            return
        field = self._fields[state["field"]]
        error = self._form.apply_answer(state["profile"], field, raw)
        if error:
            await self._io.send(update, error)
            return
        state["revision"] = None
        if state["editing"]:
            state["pending"] = [f["key"] for f in self._form.missing_fields(state["profile"])]
        await self.next_question(update, state)

    async def review(self, update, state):
        missing = self._form.missing_fields(state["profile"])
        if missing:
            state["pending"] = [f["key"] for f in missing]
            await self.next_question(update, state)
            return
        state.update(phase="review", field=None)
        await self._io.send(update, self._io.profile(state["profile"]) + "\n\nSave this profile?", [
            [("Save", f"draft:{state['token']}:save"), ("Discard", f"draft:{state['token']}:cancel")],
            [("Edit more", f"draft:{state['token']}:edit")],
        ])

    async def save(self, update, context, state):
        if state["phase"] != "review":
            await self.review(update, state)
            return False
        error = self._form.validate_for_save(state["profile"])
        if error:
            await self._io.send(update, error)
            return False
        try:
            values = self._form.storage_values(state["profile"])
            result = await asyncio.to_thread(self._users.update_user, state["student_id"], values)
            if not result.success:
                await self._io.send(update, result.error_msg + " Your draft is kept. /save retries; /cancel discards it.")
                return False
        except Exception:
            logger.exception("Telegram profile save failed")
            await self._io.send(update, "Could not save. Your draft is kept. /save retries; /cancel discards it.")
            return False
        context.user_data.pop(STATE_KEY, None)
        context.user_data.pop("browse", None)
        await self._io.send(update, "Profile saved.")
        return True

    async def callback(self, update, context, state, parts):
        if len(parts) < 3 or parts[1] != state["token"]:
            await self._io.send(update, "This draft menu has expired. Use the latest buttons.")
            return False
        if parts[0] == "field" and len(parts) == 3 and state["phase"] == "fields":
            key = parts[2]
            if key in self._fields and not self._form.should_skip(state["profile"], self._fields[key]):
                await self.prompt(update, state, key)
                return False
        elif parts[0] == "answer" and len(parts) == 4 and state["phase"] == "question" and parts[2] == state["revision"]:
            field = self._fields[state["field"]]
            action = parts[3]
            if action == "skip" and not field["required"]:
                await self.answer(update, state, "")
            elif action == "done" and field["kind"] == "multi_choice":
                raw = ",".join(str(i + 1) for i in state["selected"])
                await self.answer(update, state, raw)
            elif action.isdecimal() and field["kind"] in ("choice", "mbti", "multi_choice"):
                index = int(action)
                if not 0 <= index < len(field["options"]):
                    await self._io.send(update, "Invalid option.")
                elif field["kind"] == "multi_choice":
                    selected = state["selected"]
                    if index in selected:
                        selected.remove(index)
                    elif field["options"][index] == "No preference":
                        selected[:] = [index]
                    else:
                        selected[:] = [i for i in selected if field["options"][i] != "No preference"]
                        selected.append(index)
                    # Rotate the question token so the previous keyboard is stale.
                    state["revision"] = secrets.token_hex(3)
                    await self.question(update, state)
                else:
                    await self.answer(update, state, field["options"][index])
            else:
                await self._io.send(update, "Please use a valid option.")
            return False
        elif parts[0] == "draft" and len(parts) == 3:
            action = parts[2]
            if action == "cancel":
                context.user_data.pop(STATE_KEY, None)
                await self._io.send(update, "Draft discarded. Saved profile unchanged.")
                return True
            if action == "review":
                await self.review(update, state)
                return False
            if action == "save":
                return await self.save(update, context, state)
            if action == "edit":
                state["editing"] = True
                await self.edit_menu(update, state)
                return False
        await self._io.send(update, "This menu is no longer active. Use the latest buttons.")
        return False
