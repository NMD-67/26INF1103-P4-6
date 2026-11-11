# The auth handler for our app; responsible for handling user auth actions

from src.email import send_email
from Data_Manager.database.db import *
import random


def is_valid_student_id(student_id):
    return student_id.isnumeric() and len(str(student_id)) == 7


def get_user_info(student_id):
    """
    Returns an object {
    success: bool,
    error: str,
    user: Dict
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
    # TODO
    return
