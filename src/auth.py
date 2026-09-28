# The auth handler for our app; responsible for handling user auth actions

from src.email import send_email


async def login_user(student_id):
  print(f"Attempting to log in user with student_id: {student_id}")
  print(f"Type of student_id: {type(student_id)}")
  # Ensure student_id is the correct format
  if(not student_id.isnumeric() or len(str(student_id)) != 7):
    return 400 
  # If valid, generate an OTP and send it to the user's email
  email = f"{student_id}@sit.singaporetech.edu.sg"
  opt = "123456"  # Replace with actual OTP generation
  response = await send_email(to_email=email, subject="Your OTP for Login", html_content="Your OTP is: " + opt)  # Replace with actual OTP generation logic
  print(f"Email send response: {response is None}")
  if response is None:
    print(f"Failed to send email for student_id: {student_id}. Response: {response}")
    return 500  # Error sending email
  else:
    return 200  # Email sent successfully
  # If invalid, return an error response
  return

def validate_otp(student_id, otp):
  # Validate the OTP sent to the user's email
  # If valid, log the user in and return a success response
  # If invalid, return an error response
  return

def get_user_info(student_id):
  # Retrieve user information based on the student_id
  # Return user details if found, else return an error response
  return

def edit_user_info(student_id, new_info):
  # Update user information based on the student_id and new_info provided
  # Return a success response if updated, else return an error response
  return