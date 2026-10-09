"""Offline integration checks for spreadsheet-only profile saving."""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import db
import io_manager
from profile_schema import PROFILE_FIELDS


def run_checks():
    fields = [field["key"] for field in PROFILE_FIELDS]
    online = dict.fromkeys(fields, "")
    online.update(student_id="0123456", name="Current Name", birthday="01/01/2004",
                  mbti="INTJ", hobbies='["Reading"]', match_preference="Both",
                  insta_handle="keep online")
    worksheet = Mock()
    headers = fields + ["insta_handle"]
    worksheet.col_values.return_value = ["student_id", "0123456"]
    worksheet.row_values.side_effect = lambda row: headers if row == 1 else [online[k] for k in headers]
    with patch.object(db, "get_sheet", return_value=worksheet):
        loaded = db.get_profile("0123456")
        assert loaded["hobbies"] == ["Reading"]
        assert loaded["traits"]["western_zodiac"] == "Capricorn"
        assert loaded["insta_handle"] == "keep online"

        # Saving performs no local file I/O and only updates the edited cell.
        with patch("builtins.open", side_effect=AssertionError("No local files allowed")):
            result = db.save_profile({"student_id": "0123456", "birthday": "02/06/2004"}, partial=True)
        assert result["saved"]
        updates = worksheet.batch_update.call_args.args[0]
        assert len(updates) == 1 and updates[0]["values"] == [["02/06/2004"]]
        worksheet.append_row.assert_not_called()

        worksheet.batch_update.side_effect = RuntimeError("offline")
        result = db.save_profile({"student_id": "0123456", "hobbies": ["Swimming"]}, partial=True)
        assert not result["saved"]
        worksheet.batch_update.side_effect = None
        assert db.save_profile({"student_id": "0123456", "hobbies": ["Swimming"]}, partial=True)["saved"]

        worksheet.reset_mock()
        for ids in (["student_id"], ["student_id", "0123456", "0123456"]):
            worksheet.col_values.return_value = ids
            result = db.save_profile({"student_id": "0123456", "name": "New Name"}, partial=True)
            assert not result["saved"]
        worksheet.batch_update.assert_not_called()
        worksheet.append_row.assert_not_called()

        # Existing login helpers retain their response formats and worksheet routing.
        worksheet.col_values.return_value = ["student_id", "0123456"]
        assert db.get_user("0123456")["user"]["name"] == "Current Name"
        assert db.add_user(student_id="0123456") == 401
        worksheet.col_values.return_value = ["student_id"]
        assert db.get_user("0123456")["status"] == 404
        assert db.add_user(student_id="0123456") == 201

    from types import SimpleNamespace
    otp_sheet = Mock()
    otp_sheet.row_values.side_effect = lambda row: ["student_id", "otp", "created"] if row == 1 else ["0123456", "1234", "today"]
    otp_sheet.col_values.return_value = ["student_id", "0123456"]
    bot_sheet = Mock()
    bot_sheet.find.return_value = SimpleNamespace(row=2)
    bot_sheet.row_values.return_value = ["123", "0123456"]
    with patch.object(db, "get_sheet", side_effect=lambda name: {"otp": otp_sheet, "bot_users": bot_sheet}[name]):
        assert db.upload_otp("0123456", "1234") == 200
        assert db.get_otp("0123456")["otp"] == "1234"
        assert db.delete_otp([2]) == 200
        otp_sheet.delete_rows.assert_called_once_with(2)
        db.save_user(123, "0123456")
        bot_sheet.update_cell.assert_called_once_with(2, 2, "0123456")
        assert db.get_bot_user(123)["student_id"] == "0123456"
        bot_sheet.find.return_value = None
        db.save_user(456, "7654321")
        bot_sheet.append_row.assert_called_once_with([456, "7654321"])


if __name__ == "__main__":
    run_checks()
    io_manager.show("Shared saving checks passed (no live API calls).")
