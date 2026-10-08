from database.db import *

def add_recco_student_id(student_id, new_students):
    try:
        print(f"Addinf recco_student_id")
        result = add_to_recco_student_id(student_id, new_students)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add recco_student_id for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_recco_student_id(student_id, students_to_remove):
    try:
        print(f"Removing recco_student_id")
        result = remove_from_recco_student_id(student_id, students_to_remove)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to remove recco_student_id for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_recco_student_id(student_id):
    try:
        print(f"Getting recco_student_id")
        result = get_user_recco_student_id(student_id)
        if result["success"]:
            return {"success": True, "recco_student_id": result["recco_student_id"]}
        else:
            return {"success": False, "error": result["error"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_accepted_match(student_id, new_matches):
    try:
        print(f"Adding accepted_match")
        result = add_to_accepted_student_id(student_id, new_matches)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add accepted_match for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_accepted_match(student_id, matches_to_remove):
    try:
        print(f"Removing accepted_match")
        result = remove_from_accepted_student_id(student_id, matches_to_remove)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to remove accepted_match for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_accepted_match(student_id):
    try:
        print(f"Getting accepted_match")
        result = get_accepted_student_id(student_id)
        if result["success"]:
            return {"success": True, "accepted_student_id": result["accepted_student_id"]}
        else:
            return {"success": False, "error": result["error"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_rejected_match(student_id, new_matches):
    try:
        print(f"Adding rejected_match")
        result = add_to_rejected_student_id(student_id, new_matches)
        if result == 200:
            return {"success": True, "status": 200}
        else:
            return {"success": False, "error": f"Failed to add rejected_match for student ID {student_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
