"""Google Sheets access for profiles, login codes, and Telegram links."""
from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path

import gspread
import traceback
import logic_manager
from profile_schema import PROFILE_FIELDS

logger = logging.getLogger(__name__)
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parent / "service_account.json"
_spreadsheet = None
_worksheets = {}


def get_sheet(name):
    """Connect on first use, so importing this module needs no credentials/network."""
    global _spreadsheet
    if _spreadsheet is None:
        if not SERVICE_ACCOUNT_FILE.is_file():
            raise FileNotFoundError("service_account.json is missing")
        client = gspread.service_account(filename=str(SERVICE_ACCOUNT_FILE))
        client.set_timeout(20)
        spreadsheet_id = os.environ.get(
            "SITOGETHER_SPREADSHEET_ID", "1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU"
        )
        _spreadsheet = client.open_by_key(spreadsheet_id)
        _worksheets.clear()
    if name not in _worksheets:
        _worksheets[name] = _spreadsheet.worksheet(name)
    return _worksheets[name]


def read_profile(student_id, sheet_name="users"):
    """Read exactly one student ID;
     
    Return None if missing; 
    
    Return a dict of all columns if found;"""
    worksheet = get_sheet(sheet_name)
    headers = worksheet.row_values(1)
    column = headers.index("student_id") + 1
    matches = []
    for row, value in enumerate(worksheet.col_values(column), start=1):
        if row > 1 and str(value) == str(student_id):
            matches.append(row)
    if len(matches) > 1:
        raise ValueError("Duplicate student IDs need review")
    if not matches:
        return None
    values = worksheet.row_values(matches[0])
    values += [""] * (len(headers) - len(values))
    return dict(zip(headers, values))


def safe_json_load(value):
    """Convert a string to a JSON object if possible; otherwise return the original value."""
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value

def get_header_values(sheet: gspread.Worksheet):
    """
    Returns an array of header values"""
    headers = sheet.row_values(1)
    return headers

def column_name_exists(worksheet, column_name):
    """
    Check if a column name exists in the worksheet"""
    headers = get_header_values(worksheet)
    if column_name not in headers:
        return False
    else:
        return True

def get_row_numbers_by_column_name(worksheet, column_name, value):
    """
    Used to get all the rows where the column value matches the given value

    returns an object {
        success: bool,
        error: str,
        rows: List
    }
    """
    headers = get_header_values(sheet=worksheet)
    if column_name not in headers:
        return {"success": False, "error": f"Column name {column_name} not found"}
    col_index = headers.index(column_name) + 1
    col_values = worksheet.col_values(col_index)

    matching_rows = [
        i + 1 for i, v in enumerate(col_values)
        if v == value and i != 0
    ]

    try:
      return {"success": True, "rows": matching_rows}
    except ValueError:
        return {"success": False, "error": f'Value {value} not found in column'}
    
def get_cell_value(worksheet, row_number, column_name):
    """
    Returns the value of a cell given the row number and column name"""
    headers = get_header_values()
    if not column_name_exists(worksheet=worksheet, column_name=column_name):
        return {"success": False, "error": f"Column {column_name} doesn't exist"}

    col_index = headers.index(column_name) + 1
    value = worksheet.cell(row_number, col_index).value
    return {"success": True, "value": value}

def delete_row(worksheet: gspread.Worksheet, row_number):
    print(f'Deleting row {row_number} from {worksheet}')
    try:
        worksheet.delete_rows(row_number)
        return 200
    except Exception as e:
        print(f'An error occured deleting row: {e}')
        

def get_row_values(worksheet, row_numbers):
  """
  Returns an array of dicts containing the column names and values
  """
  values = []
  for row_number in row_numbers:
    headers = get_header_values(worksheet)
    row_values = worksheet.row_values(row_number)

    row_values += [""] * (len(headers) - len(row_values))

    print(row_values)
    values.append(dict(zip(headers, row_values)))

  return values

def update_field(worksheet, row, col, value):
    """
    Update a specific cell in the worksheet given the row number, column number, and new value"""
    worksheet.update_cell(row, col, value)

def convert_list_to_dict(headers, values):
    """
    Convert a list of headers and a list of values into a dictionary"""
    if len(headers) != len(values):
        raise ValueError("Headers and values must have the same length")
    return dict(zip(headers, values))

# ---OTP Functions---
def upload_otp(student_id, otp):
    try:
      current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      row = [student_id, otp, current_datetime]
      get_sheet("otp").append_row(row)
      return 200
    except Exception as e:
        print(f"An error occured when creating otp: {e}")
        return 500

def get_otp(student_id):
    try:
      user_row_number = get_row_numbers_by_column_name(get_sheet("otp"), "student_id", student_id)
      print(f"User row number: {user_row_number}")
      if not user_row_number["success"]:
          return 500
      user_row = get_row_values(get_sheet("otp"), user_row_number["rows"])
      if user_row is None or len(user_row) < 1:
          return 404
      print(user_row)
      return {"row_numbers": user_row_number["rows"], "otp": user_row[0]["otp"]}
    except Exception as e:
        print(f"An error occured when checking otp: {e}")
        return 500

def delete_otp(row_numbers):
  try:  
    print(f'Delting otp {row_numbers}')
    i = 0
    for row_number in row_numbers:
      print(f"Deleting otp row {row_number}")
      res = get_sheet("otp").delete_rows(row_number - i)
      i += 1
      print(res)
    return 200
  except Exception as e:
      print(f"Error deleting otp row {row_number}: {e}")
      return 500

# ---Bot Functions---
def save_user(tele_id, student_id):
    # Check if user alr exists
    cell = get_sheet("bot_users").find(str(tele_id))
    if cell:
        get_sheet("bot_users").update_cell(cell.row, 2, student_id)
    else:
        get_sheet("bot_users").append_row([tele_id, student_id])

def get_bot_user(tele_id):
    cell = get_sheet("bot_users").find(str(tele_id))
    if(cell):
        row = get_sheet("bot_users").row_values(cell.row)
        student_id = row[1]
        return {"tele_id": tele_id, "student_id": student_id}
    return None

# ---User Functions---
def get_user(student_id):
    """Returns: {success: bool, error: str, status: int, user: dict} User is a dict of all columns if found, else None"""
    try:
        user = read_profile(student_id)
        if user is None:
            return {"success": False, "error": "User not found!", "status": 404}
        return {"success": True, "user": user, "status": 200}
    except Exception as error:
        logger.warning("Could not read user (%s)", type(error).__name__)
        return {"success": False, "error": "Could not read user", "status": 500}


def add_user(**fields):
    """
    fields: any combination of column_name=value, e.g.
        add_user(student_id="676767", name="Alice", bio="hi")
    """
    if "student_id" not in fields:
        return 400
    try:
        headers = get_sheet("users").row_values(1)  # actual column order in the sheet

        row = []  # build row matching sheet's real column order
        for column in headers:
            value = fields.get(column, "") #Get the value at the column, default ""
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            row.append(value)

        # Check if user exists
        user_result = get_user(fields["student_id"])
        if user_result["success"]:
            return 401
        if user_result.get("status") != 404:
            return 500
        res = get_sheet("users").append_row(row)
        print(f"res: {res}")
        return 201
    except Exception as e:
        print(f"Error when adding user: {e}")
        return 500

def update_user(**student_details):
    """
    student_details: any combination of column_name=value, e.g.
        update_user(student_id="676767", name="Alice", bio="hi")
    """
    try:
        print("Updating user")
        headers = get_header_values(get_sheet("users"))
        if "student_id" not in student_details:
            return 400
        student_id = student_details.get("student_id")
        user_response = get_sheet("users").find(str(student_id))
        if user_response is None:
            return 404
        row = user_response.row
        if row is None:
            return 404

        for index, column in enumerate(headers):
            if column in student_details and column != "student_id":
                print(f"Col: {column}, row: {row}, index: {index}, value: {student_details.get(column)}")
                value = safe_json_load(student_details.get(column))
                get_sheet("users").update_cell(row, index + 1, value)
        return 200
    except gspread.exceptions.APIError as e:
        print(f"API error while updating user: {e}")
        return 500  # API error
    except gspread.exceptions.CellNotFound:
        print(f"Cell not found while updating user with student_id {student_id}.")
        return 404  # User not found
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet not found while updating user with student_id {student_id}.")
        return 404  # User not found
    except gspread.exceptions.RequestError as e:
        print(f"Request error while updating user: {e}")
        return 500  # Request error
    except Exception as e:
        print(f"Error updating user: {e}")
    return 500

def delete_user(student_id):
    try:  
      print(f"Deleting student {student_id}")
      row_number = get_row_numbers_by_column_name(get_sheet("users"), "student_id", student_id)

      res = get_sheet("otp").delete_rows(row_number[0])
      print(res)
      return 200
    except Exception as e:
        print(f"Error deleting otp row {row_number}: {e}")
        return 500

# get_otp("2603197")
#get_row_values(get_sheet("otp"), 2)
#print(get_user("2676767"))
# student_json = {"student_id": "234567", "name": "Giggg"}
# print(update_user(**student_json))
# get_header_values(get_sheet("users"))

def sync_profile_to_sheets(profile: dict, partial=False) -> tuple[bool, str]:
    """Upload one profile; preserve all sheet fields outside the profile form.

    A partial edit writes only supplied form fields and requires an existing row.
    Lists display as comma-separated text; empty lists display as blank cells.
    Traits and completeness are calculated by the caller when needed.
    """
    try:
        worksheet = get_sheet("users")
        headers = worksheet.row_values(1)
        # Check the spreadsheet columns before writing anything.
        fields = []
        for field in PROFILE_FIELDS:
            fields.append(field["key"])
        if len(headers) != len(set(headers)):
            return False, "Google Sheets sync stopped: users headers are missing or duplicated."
        for key in fields:
            if key not in headers:
                return False, "Google Sheets sync stopped: users headers are missing or duplicated."
            if not partial and key not in profile:
                return False, "Google Sheets sync stopped: the profile is missing form fields."
        if "match_preference" in profile and profile["match_preference"] not in ("Male", "Female", "Both"):
            return False, "Google Sheets sync stopped: please re-enter your match preference."

        # For an edit, include only the fields that the caller supplied.
        if partial:
            changed_fields = []
            for key in fields:
                if key in profile:
                    changed_fields.append(key)
            fields = changed_fields
        student_id = str(profile["student_id"])
        id_column = headers.index("student_id") + 1
        matches = []
        for row, value in enumerate(worksheet.col_values(id_column), start=1):
            if row > 1 and str(value) == student_id:
                matches.append(row)
        if len(matches) > 1:
            return False, "Google Sheets sync stopped: duplicate student IDs need review."

        values = {}
        for key in fields:
            value = profile[key]
            if isinstance(value, list):
                clean_items = []
                for item in value:
                    if item is None:
                        continue
                    item_text = str(item).strip()
                    if item_text:
                        clean_items.append(item_text)
                value = ", ".join(clean_items)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            if value is None:
                values[key] = ""
            else:
                values[key] = str(value)

        if matches:
            # Write only owned fields, retaining Instagram and any other columns.
            from gspread.utils import rowcol_to_a1
            updates = []
            row = matches[0]
            for key in fields:
                if key == "student_id":
                    continue
                column = headers.index(key) + 1
                cell = rowcol_to_a1(row, column)
                updates.append({"range": cell, "values": [[values[key]]]})
            worksheet.batch_update(updates, value_input_option="RAW")
        elif partial:
            return False, "Profile not found. Please complete /setup first."
        else:
            new_row = []
            for header in headers:
                new_row.append(values.get(header, ""))
            worksheet.append_row(new_row, value_input_option="RAW")
        return True, "Profile synced to Google Sheets."
    except Exception as error:
        # Never print credentials, API response bodies or personal data.
        logger.warning("Google Sheets sync failed (%s)", type(error).__name__)
        return False, "Google Sheets sync failed. Check spreadsheet access and connection."


# Profile functions used by the CLI and Telegram. Keep these signatures
# and return values stable when replacing the storage backend.
def get_profile(student_id):
    """Read one profile. Return None if missing; let the caller handle outages."""
    profile = read_profile(student_id)
    if profile is None:
        return None
    profile = normalize_profile(profile)
    # Derived information is calculated when needed, not stored in a second file.
    try:
        profile["traits"] = logic_manager.derive_profile_traits(profile)
    except (ValueError, TypeError, KeyError):
        profile["traits"] = {}
    profile["profile_complete"] = logic_manager.is_profile_complete(profile, PROFILE_FIELDS)
    return profile


def save_profile(profile, partial=False):
    """Save to Sheets. Only report success when the spreadsheet confirms it."""
    saved, message = sync_profile_to_sheets(profile, partial=partial)
    return {"saved": saved, "message": message}


def normalize_profile(profile):
    """Convert spreadsheet list cells into Python lists for the form code."""
    result = profile.copy()
    for field in PROFILE_FIELDS:
        key = field["key"]
        value = result.get(key)
        if field["kind"] != "list":
            if key not in result:
                result[key] = None
            continue

        if isinstance(value, str):
            # Support both historical JSON cells and current comma-separated cells.
            try:
                decoded = json.loads(value)
            except ValueError:
                decoded = None
            if isinstance(decoded, list):
                value = decoded
            else:
                value = value.split(",")

        clean_items = []
        if value is not None:
            for item in value:
                if item is None:
                    continue
                item_text = str(item).strip()
                if item_text:
                    clean_items.append(item_text)
        result[key] = clean_items
    return result

# --------Matches---------
def get_user_row(student_id):
    """
    Returns an array of row values 
    """
    worksheet = get_sheet("matches")
    row_numbers = get_row_numbers_by_column_name(worksheet, "student_id", student_id)
    if not row_numbers["success"]:
        return {"success": False, "error": row_numbers.get("error", "Unknown error")}
    if not row_numbers["rows"]:
        return {"success": False, "error": f"Student ID {student_id} not found"}
    row_values = get_row_values(worksheet, row_numbers["rows"])[0]
    return {"success": True, "row_values": row_values}

def get_user_recco_student_id(student_id):
    """
    Returns the recco_student_id for a given student_id
    returns an object {
        success: bool,
        error: str,
        recco_student_id: dict {
            student_id: compatibility_score
        }}
    """
    user_row = read_profile(student_id, sheet_name="matches")
    if user_row is None:
        return {"success": False, "error": f"Student ID {student_id} not found"}
    user_recco_student_id = user_row.get("recco_student_id")
    if user_recco_student_id is None or user_recco_student_id == "":
        return {"success": True, "error": None, "recco_student_id": {}}
    try:
        recco_student_id_dict = json.loads(user_recco_student_id)
        return {"success": True, "error": None, "recco_student_id": recco_student_id_dict}
    except json.JSONDecodeError:
        return {"success": False, "error": f"Invalid JSON format for recco_student_id for student ID {student_id}"}

def add_user_matches_row(student_id):
    try:
        worksheet = get_sheet("matches")
        headers = worksheet.row_values(1)
        if "student_id" not in headers:
            return 400
        row = []
        for column in headers:
            row.append(student_id if column == "student_id" else "")
        worksheet.append_row(row)
        return 200
    except Exception as e:
        print(f"Error when adding user row to matches: {e}")
        return 500

def update_matches_column(student_id, column_name, new_value):
    try:
        print(f"Updating {column_name} for student {student_id} to {new_value}")
        worksheet = get_sheet("matches")
        headers = worksheet.row_values(1)
        if "student_id" not in headers or column_name not in headers:
            return 400
        student_id_col = headers.index("student_id") + 1
        column_col = headers.index(column_name) + 1
        matches = []
        for row, value in enumerate(worksheet.col_values(student_id_col), start=1):
            if row > 1 and str(value) == str(student_id):
                matches.append(row)
        if len(matches) > 1:
            return 400
        if not matches:
            return 404
        row_number = matches[0]
        worksheet.update_cell(row_number, column_col, new_value)
        return 200
    except Exception as e:
        print(f"Error when updating {column_name}: {e}")
        return 500

def add_to_recco_student_id(student_id: str, new_students: dict):
    """
    Add new students to a specific student's recco_student_id column in the matches sheet
    Parameters:
    student_id (str): The student ID of the user to update
    new_students (dict): A dictionary containing the new students to add in the format {student_id: compatibility_score}
    """
    try:
        # Get the matches worksheet
        # Get user's row/current recco_student_id value
        # Check if student_id exists
        print(f"Adding to recco_student_id for student {student_id} with new students {new_students}")
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            add_user_matches_row(student_id)
        current_recco_student_id = user_profile.get("recco_student_id")
        if current_recco_student_id is None or current_recco_student_id == "":
          current_recco_student_id = {}
        else:
          current_recco_student_id = json.loads(current_recco_student_id)
        for new_student_id, score in new_students.items():
          current_recco_student_id[new_student_id] = score
        return update_matches_column(student_id, "recco_student_id", json.dumps(current_recco_student_id))
    except json.JSONDecodeError:
        return 500
    except Exception as e:
        traceback.print_exc()
        print(f"Error when adding to recco_student_id: {e}")
        return 500

def remove_from_recco_student_id(student_id: str, students_to_remove: list):
    """
    Remove students from a specific student's recco_student_id column in the matches sheet
    Parameters:
    student_id (str): The student ID of the user to update
    students_to_remove (list): A list of student IDs to remove from the recco_student_id column
    """
    try:
        print(f"Removing from recco_student_id for student {student_id} with students to remove {students_to_remove}")
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return 404
        current_recco_student_id = user_profile.get("recco_student_id")
        if current_recco_student_id is None or current_recco_student_id == "":
          current_recco_student_id = {}
        else:
          current_recco_student_id = json.loads(current_recco_student_id)
        for student_to_remove in students_to_remove:
          if student_to_remove in current_recco_student_id:
            del current_recco_student_id[student_to_remove]
        return update_matches_column(student_id, "recco_student_id", json.dumps(current_recco_student_id))
    except json.JSONDecodeError:
        return 500
    except Exception as e:
        traceback.print_exc()
        print(f"Error when removing from recco_student_id: {e}")
        return 500

def add_to_accepted_student_id(student_id: str, new_students: list):
    """
    Add new students to a specific student's accepted_student_id column in the matches sheet
    Parameters:
    student_id (str): The student ID of the user to update
    new_students (list): A list of student IDs to add to the accepted_student_id column
    """
    try:
        print(f"Adding to accepted_student_id for student {student_id} with new students {new_students}")
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return 404
        current_accepted_student_id = user_profile.get("accepted_student_id")
        if current_accepted_student_id is None or current_accepted_student_id == "":
          current_accepted_student_id = []
        else:
          current_accepted_student_id = json.loads(current_accepted_student_id)
        for new_student in new_students:
          if new_student not in current_accepted_student_id:
            current_accepted_student_id.append(new_student)
        return update_matches_column(student_id, "accepted_student_id", json.dumps(current_accepted_student_id))
    except json.JSONDecodeError:
        return 500
    except Exception as e:
        traceback.print_exc()
        print(f"Error when adding to accepted_student_id: {e}")
        return 500

def remove_from_accepted_student_id(student_id: str, students_to_remove: list):
    """
    Remove students from a specific student's accepted_student_id column in the matches sheet
    Parameters:
    student_id (str): The student ID of the user to update
    students_to_remove (list): A list of student IDs to remove from the accepted_student_id column
    """
    try:
        print(f"Removing from accepted_student_id for student {student_id} with students to remove {students_to_remove}")
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return 404
        current_accepted_student_id = user_profile.get("accepted_student_id")
        if current_accepted_student_id is None or current_accepted_student_id == "":
          current_accepted_student_id = []
        else:
          current_accepted_student_id = json.loads(current_accepted_student_id)
        for student_to_remove in students_to_remove:
          if student_to_remove in current_accepted_student_id:
            current_accepted_student_id.remove(student_to_remove)
        return update_matches_column(student_id, "accepted_student_id", json.dumps(current_accepted_student_id))
    except json.JSONDecodeError:
        return 500
    except Exception as e:
        traceback.print_exc()
        print(f"Error when removing from accepted_student_id: {e}")
        return 500

def get_accepted_student_id(student_id: str):
    """
    Get the accepted_student_id for a specific student from the matches sheet
    Parameters:
    student_id (str): The student ID of the user to retrieve the accepted_student_id for
    Returns:
    dict: A dictionary containing the success status, error message (if any), and the accepted_student_id list
    """
    try:
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return {"success": False, "error": f"Student ID {student_id} not found", "accepted_student_id": []}
        current_accepted_student_id = user_profile.get("accepted_student_id")
        if current_accepted_student_id is None or current_accepted_student_id == "":
            return {"success": True, "error": None, "accepted_student_id": []}
        else:
            current_accepted_student_id = json.loads(current_accepted_student_id)
            return {"success": True, "error": None, "accepted_student_id": current_accepted_student_id}
    except json.JSONDecodeError:
        return {"success": False, "error": f"Invalid JSON format for accepted_student_id for student ID {student_id}", "accepted_student_id": []}
    except Exception as e:
        traceback.print_exc()
        print(f"Error when getting accepted_student_id: {e}")
        return {"success": False, "error": f"Error when getting accepted_student_id: {e}", "accepted_student_id": []}

def get_rejected_student_id(student_id: str):
    """
    Get the rejected_student_id for a specific student from the matches sheet
    Parameters:
    student_id (str): The student ID of the user to retrieve the rejected_student_id for
    Returns:
    dict: A dictionary containing the success status, error message (if any), and the rejected_student_id list
    """
    try:
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return {"success": False, "error": f"Student ID {student_id} not found", "rejected_student_id": []}
        current_rejected_student_id = user_profile.get("rejected_student_id")
        if current_rejected_student_id is None or current_rejected_student_id == "":
            return {"success": True, "error": None, "rejected_student_id": []}
        else:
            current_rejected_student_id = json.loads(current_rejected_student_id)
            return {"success": True, "error": None, "rejected_student_id": current_rejected_student_id}
    except json.JSONDecodeError:
        return {"success": False, "error": f"Invalid JSON format for rejected_student_id for student ID {student_id}", "rejected_student_id": []}
    except Exception as e:
        traceback.print_exc()
        print(f"Error when getting rejected_student_id: {e}")
        return {"success": False, "error": f"Error when getting rejected_student_id: {e}", "rejected_student_id": []}

def add_to_rejected_student_id(student_id: str, new_students: list):
    """
    Add new students to a specific student's rejected_student_id column in the matches sheet
    Parameters:
    student_id (str): The student ID of the user to update
    new_students (list): A list of student IDs to add to the rejected_student_id column
    """
    try:
        print(f"Adding to rejected_student_id for student {student_id} with new students {new_students}")
        user_profile = read_profile(student_id, sheet_name="matches")
        if user_profile is None:
            return 404
        current_rejected_student_id = user_profile.get("rejected_student_id")
        if current_rejected_student_id is None or current_rejected_student_id == "":
          current_rejected_student_id = []
        else:
          current_rejected_student_id = json.loads(current_rejected_student_id)
        for new_student in new_students:
          if new_student not in current_rejected_student_id:
            current_rejected_student_id.append(new_student)
        return update_matches_column(student_id, "rejected_student_id", json.dumps(current_rejected_student_id))
    except json.JSONDecodeError:
        return 500
    except Exception as e:
        traceback.print_exc()
        print(f"Error when adding to rejected_student_id: {e}")
        return 500

#print(add_to_accepted_student_id("1009", ["7654321", "9876543"]))
# print(remove_from_accepted_student_id("1009", ["7654321"]))
# print(get_rejected_student_id("1009"))
# print(get_accepted_student_id("1009"))
# print(add_to_rejected_student_id("1009", ["7654321", "9876543"]))