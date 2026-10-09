from database.db import *

def add_recco_student_id(student_id, new_students):
    """
    Adds new recommended student IDs to the existing list for a given student ID.
    return a dict: {
        "success": True/False,
        "status": 200/400/500,
        "error": "Error message if any"}"""
    try:
        print(f"Matches: Adding recco_student_id")
        result = add_to_recco_student_id(student_id, new_students)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add recco_student_id for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_recco_student_id(student_id, students_to_remove):
    """ Removes specified recommended student IDs from the existing list for a given student ID.
    return a dict: {
        "success": True/False,
        "status": 200/400/500,
        "error": Error message if any}"""
    try:
        print(f"Matches: Removing recco_student_id")
        result = remove_from_recco_student_id(student_id, students_to_remove)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to remove recco_student_id for student ID {student_id}", "status": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_recco_student_id(student_id):
    """ Retrieves the list of recommended student IDs for a given student ID.
    return a dict: {
        "success": True/False,
        "recco_student_id": dict {
          student_id: compatibility_score,
          }
        "error": Error message if any}"""
    try:
        print(f"Matches: Getting recco_student_id")
        result = get_user_recco_student_id(student_id)
        if result["success"]:
            return {"success": True, "recco_student_id": result["recco_student_id"]}
        else:
            return {"success": False, "error": result["error"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_accepted_match(student_id, new_matches):
    """
    Adds new accepted matches to the existing list for a given student ID.
    return a dict: {
        "success": True/False,
        "status": 200/400/500,
        "error": Error message if any}"""
    try:
        print(f"Matches: Adding accepted_match")
        result = add_to_accepted_student_id(student_id, new_matches)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add accepted_match for student ID {student_id}", "status": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_accepted_match(student_id, matches_to_remove):
    """ Removes specified accepted matches from the existing list for a given student ID.
    return a dict: {
        "success": True/False,
        "status": 200/400/500,
        "error": Error message if any}"""
    try:
        print(f"Matches: Removing accepted_match")
        result = remove_from_accepted_student_id(student_id, matches_to_remove)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to remove accepted_match for student ID {student_id}", "status": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_accepted_match(student_id):
    """ Retrieves the list of accepted matches for a given student ID.
    return a dict: {
        "success": True/False,
        "accepted_student_id": dict {
          student_id: compatibility_score,
        },
        "error": Error message if any}"""
    try:
        print(f"Matches: Getting accepted_match")
        result = get_accepted_student_id(student_id)
        if result["success"]:
            return {"success": True, "accepted_student_id": result["accepted_student_id"]}
        else:
            return {"success": False, "error": result["error"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_rejected_match(student_id, new_matches):
    """
    Adds new rejected matches to the existing list for a given student ID.
    return a dict: {
        "success": True/False,
        "status": 200/400/500,
        "error": Error message if any}"""
    try:
        print(f"Matches: Adding rejected_match")
        result = add_to_rejected_student_id(student_id, new_matches)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add rejected_match for student ID {student_id}", "status": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
