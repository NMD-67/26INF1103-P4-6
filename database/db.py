import gspread
from google.oauth2.service_account import Credentials
import os
import datetime
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "service_account.json")

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("SITogether")
user_sheet = sheet.worksheet("users")
otp_sheet = sheet.worksheet("otp")
bot_sheet = sheet.worksheet("bot_users")

def safe_json_load(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value

def get_header_values(sheet: gspread.Worksheet):
    headers = sheet.row_values(1)
    return headers

def column_name_exists(worksheet, column_name):
    headers = get_header_values(worksheet)
    if column_name not in headers:
        return False
    else:
        return True

def get_row_numbers_by_column_name(worksheet, column_name, value):
    """
    Used to get all the rows where the column value matches the given value
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
  Returns an array of row value arrays
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
    worksheet.update_cell(row, col, value)

# ---OTP Functions---
def upload_otp(student_id, otp):
    try:
      current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      row = [student_id, otp, current_datetime]
      otp_sheet.append_row(row)
      return 200
    except Exception as e:
        print(f"An error occured when creating otp: {e}")
        return 500

def get_otp(student_id):
    try:
      user_row_number = get_row_numbers_by_column_name(otp_sheet, "student_id", student_id)
      print(f"User row number: {user_row_number}")
      if not user_row_number["success"]:
          return 500
      user_row = get_row_values(otp_sheet, user_row_number["rows"])
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
      res = otp_sheet.delete_rows(row_number - i)
      i += 1
      print(res)
    return 200
  except Exception as e:
      print(f"Error deleting otp row {row_number}: {e}")
      return 500

# ---Bot Functions---
def save_user(tele_id, student_id):
    # Check if user alr exists
    cell = bot_sheet.find(str(tele_id))
    if cell:
        bot_sheet.update_cell(cell.row, 2, student_id)
    else:
        bot_sheet.append_row([tele_id, student_id])

def get_bot_user(tele_id):
    cell = bot_sheet.find(str(tele_id))
    if(cell):
        row = bot_sheet.row_values(cell.row)
        student_id = row[1]
        return {"tele_id": tele_id, "student_id": student_id}
    return None

# ---User Functions---
def get_user(student_id):
    """
    Returns a response dict {
    "success": bool,
    "status": int,
    "error": str,
    "user": dict
    }
    """
    print(f'Getting user: {student_id}')
    try:
        user = user_sheet.find(student_id)

        if user is None:
            return {"success": False, "error": "User not found!", "status": 404}
        user_rows = get_row_values(user_sheet, [user.row])

        if len(user_rows) < 1:
            return {"success": False, "error": "User not found!", "status": 404}

        user = user_rows[0]
        #TODO: Convert arrays from string into list
        return {"success": True, "user": user, "status": 200}
    except gspread.exceptions.CellNotFound:
        return {"success": False, "error": "User not found!"}

def add_user(**fields):
    """
    fields: any combination of column_name=value, e.g.
        add_user(student_id="676767", name="Alice", bio="hi")
    """
    if "student_id" not in fields:
        return 400
    try:
        headers = user_sheet.row_values(1)  # actual column order in the sheet

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
        res = user_sheet.append_row(row)
        print(f"res: {res}")
        return 201
    except Exception as e:
        print(f"Error when adding user: {e}")
        return 500

def update_user(**student_details):
    try:
        print("Updating user")
        headers = get_header_values(user_sheet)
        if "student_id" not in student_details:
            return 400
        student_id = student_details.get("student_id")
        user_response = user_sheet.find(str(student_id))
        if user_response is None:
            return 404
        row = user_response.row
        if row is None:
            return 404

        for index, column in enumerate(headers):
            if column in student_details and column != "student_id":
                print(f"Col: {column}, row: {row}, index: {index}, value: {student_details.get(column)}")
                value = safe_json_load(student_details.get(column))
                user_sheet.update_cell(row, index + 1, value)
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
      row_number = get_row_numbers_by_column_name(user_sheet, "student_id", student_id)

      res = otp_sheet.delete_rows(row_number[0])
      print(res)
      return 200
    except Exception as e:
        print(f"Error deleting otp row {row_number}: {e}")
        return 500

# get_otp("2603197")
#get_row_values(otp_sheet, 2)
#print(get_user("2676767"))
# student_json = {"student_id": "234567", "name": "Giggg"}
# print(update_user(**student_json))
# get_header_values(user_sheet)