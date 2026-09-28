# The auth handler for our app; responsible for handling user auth actions

from src.email import send_email
from database.db import *
import random

def is_valid_student_id(student_id):
  return (student_id.isnumeric() and len(str(student_id)) == 7)

async def login_user(student_id):
  print(f"Attempting to log in user with student_id: {student_id}")

  # Ensure student_id is the correct format
  if(not is_valid_student_id(student_id)):
    return 400 
  
  # If valid, generate an OTP and send it to the user's email
  email = f"{student_id}@sit.singaporetech.edu.sg"
  otp = create_otp(student_id)  
  if otp is None:
    return 500
  response = await send_email(to_email=email, subject="Your OTP for Login", html_content=f"Your OTP is: {otp}")  
  print(f"Email send response: {response}")
  if response is None:
    print(f"Failed to send email for student_id: {student_id}. Response: {response}")
    return 500  # Error sending email
  else:
    return 200  # Email sent successfully

def create_otp(student_id):
  print("Creating otp")
  if not is_valid_student_id(student_id):
    return 400
  else:
    # Check if otp alr exists
    res = get_otp(student_id)

    print(f"get otp res {res}")

    # Delete otp if alr exist
    if isinstance(res, dict) and res["row_numbers"] is not None:
      delete_otp(res["row_numbers"])

    # Generate new OTP
    otp = random.randrange(1, 9999)
    result = upload_otp(student_id=student_id, otp=otp)
    print("result: ", result)
    if result == 200:
      return otp
    else:
      print("An error creating otp: " + result)
      return None


def validate_otp(student_id, otp):
  # Validate the OTP sent to the user's email
  print(f'Validating OTP for {student_id}')
  if not is_valid_student_id(student_id=student_id):
    return 400

  user_row_result = get_otp(student_id)
  print(f'validate otp user_row_result {user_row_result}')
  if not isinstance(user_row_result, dict):
    return user_row_result
  correct_otp = user_row_result["otp"]
  verified = correct_otp == otp
  if not verified:
    return 403
  else:
    print(f'validation success! user row: {user_row_result}')
    delete_otp(user_row_result["row_numbers"])

    #Check if user exist
    user_info = get_user_info(student_id)
    if  user_info.get("status") == 404:
      result = add_user(student_id=student_id)
      return result
    #IF user not exist, create user
    return 200
  
  # If valid, log the user in and return a success response
  # If invalid, return an error response

def get_user_info(student_id):
  """
  Returns an object {
  success: bool,
  error: str,
  user: List
  }
  """
  # Retrieve user information based on the student_id
  user = get_user(student_id=student_id)
  return user

def edit_user_info(student_id: str, new_info: dict):
  # Update user information based on the student_id and new_info provided
  if not is_valid_student_id(student_id):
    return 400

  new_info["student_id"] = student_id
  
  update_response = update_user(**new_info)
  if update_response == 200:
    return {"success": True, "status": 200}
  # Return a success response if updated, else return an error response
  return {"success": False, "status": update_response}

def delete_user(student_id):
  #TODO
  return