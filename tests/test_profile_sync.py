"""Offline regression checks: run py tests/test_profile_sync.py."""
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import db
import io_manager
import main
from profile_schema import PROFILE_FIELDS


def run_checks():
    fields = [field["key"] for field in PROFILE_FIELDS]
    profile = dict.fromkeys(fields, "test")
    profile.update(student_id="0123456", match_preference="Both",
                   hobbies=["Reading", "Swimming"], bio=None,
                   ccas=[], events=[""], interest_groups=["  ", None])
    headers = fields[::-1] + ["admin_notes", "extra_notes"]
    worksheet = Mock()
    worksheet.row_values.return_value = headers
    worksheet.col_values.return_value = ["student_id", "0123456"]
    client = Mock()
    client.open_by_key.return_value.worksheet.return_value = worksheet
    api = ModuleType("gspread")
    api.service_account = Mock(return_value=client)
    utils = ModuleType("gspread.utils")
    utils.rowcol_to_a1 = lambda row, col: f"{chr(64 + col)}{row}"

    with patch.object(db, "gspread", api), patch.dict(sys.modules, {"gspread.utils": utils}), patch.object(
        Path, "is_file", return_value=True
    ):
        # Existing profile: preserve non-profile columns and target the ID column.
        assert db.sync_profile_to_sheets(profile)[0]
        worksheet.col_values.assert_called_with(headers.index("student_id") + 1)
        updates = worksheet.batch_update.call_args.args[0]
        assert len(updates) == len(fields) - 1
        assert all(item["range"] not in (utils.rowcol_to_a1(2, len(fields) + 1), utils.rowcol_to_a1(2, len(fields) + 2)) for item in updates)
        hobby_cell = utils.rowcol_to_a1(2, headers.index("hobbies") + 1)
        assert next(item["values"][0][0] for item in updates if item["range"] == hobby_cell) == 'Reading, Swimming'
        for key in ("ccas", "events", "interest_groups"):
            cell = utils.rowcol_to_a1(2, headers.index(key) + 1)
            assert next(item["values"][0][0] for item in updates if item["range"] == cell) == ""
        assert profile["hobbies"] == ["Reading", "Swimming"]
        worksheet.append_row.assert_not_called()

        # New profile: preserve header order, ID text, blanks, and literal input.
        worksheet.col_values.return_value = ["student_id"]
        assert db.sync_profile_to_sheets(profile)[0]
        args, kwargs = worksheet.append_row.call_args
        assert args[0][headers.index("student_id")] == "0123456"
        assert args[0][headers.index("bio")] == ""
        assert args[0][headers.index("hobbies")] == "Reading, Swimming"
        for key in ("ccas", "events", "interest_groups"):
            assert args[0][headers.index(key)] == ""
        assert kwargs["value_input_option"] == "RAW"

        # Ambiguous IDs or a mismatched schema must not write anything.
        worksheet.reset_mock()
        worksheet.col_values.return_value = ["student_id", "0123456", "0123456"]
        assert not db.sync_profile_to_sheets(profile)[0]
        worksheet.row_values.return_value = ["student_id", "name"]
        assert not db.sync_profile_to_sheets(profile)[0]
        worksheet.batch_update.assert_not_called()
        worksheet.append_row.assert_not_called()

        # Authentication/network failures return a safe error rather than crash.
        db._spreadsheet = None
        api.service_account.side_effect = RuntimeError("sensitive response")
        ok, message = db.sync_profile_to_sheets(profile)
        assert not ok and "sensitive response" not in message

    with patch.object(Path, "is_file", return_value=False):
        assert not db.sync_profile_to_sheets(profile)[0]

    # CLI read failures stop setup, rather than treating the user as missing.
    with patch.object(db, "get_profile", side_effect=RuntimeError("offline")), patch.object(
        io_manager, "ask_field", return_value="0123456"
    ), patch.object(io_manager, "show"), patch.object(io_manager, "show_error") as error, patch.object(
        io_manager, "collect_profile"
    ) as collect:
        main.run_profile_setup()
        error.assert_called_once()
        collect.assert_not_called()

    # No success message is displayed for a failed spreadsheet write.
    with patch.object(db, "get_profile", return_value=None), patch.object(
        io_manager, "ask_field", return_value="0123456"
    ), patch.object(io_manager, "confirm", return_value=True), patch.object(
        io_manager, "collect_profile", return_value=profile.copy()
    ), patch.object(io_manager, "show_profile_summary"), patch.object(io_manager, "show") as show, patch.object(
        io_manager, "show_error"
    ) as error, patch.object(main.logic_manager, "derive_profile_traits", return_value={}), patch.object(
        db, "sync_profile_to_sheets", return_value=(False, "Offline")
    ):
        main.run_profile_setup()
        error.assert_called_once_with("Offline")
        assert all(call.args[0] != "Profile saved." for call in show.call_args_list)


if __name__ == "__main__":
    run_checks()
    io_manager.show("Profile sync checks passed (no live API calls).")
