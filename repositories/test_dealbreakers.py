import os
from pathlib import Path
import sys
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, pool
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Data_Manager.repositories.user_repo import UserRepo
from Logic_Manager.services.user_service import UserService   # adjust to your real path
from results.success import Success
from results.error import Error
from dotenv import load_dotenv


load_dotenv()
DB_URL = os.environ["SUPABASE_URL"]   # or rename the key in .env to DATABASE_URL, which is clearer

def violations(repo: UserRepo, user, d: dict) -> list[str]:
  """Which of the dealbreaker criteria this user fails. Empty list means they pass."""
  failed = []

  if d.get("gender") and user.gender != d["gender"]:
    failed.append("gender")

  min_age, max_age = d.get("min_age"), d.get("max_age")
  if min_age is not None or max_age is not None:
    age = user.age
    if age is None or (min_age is not None and age < min_age) or (max_age is not None and age > max_age):
      failed.append("age")

  if d.get("religion") and user.religion not in d["religion"]:
    failed.append("religion")

  if d.get("race"):
    # adjust the attribute name to wherever your User model keeps race
    if not UserRepo._overlaps(getattr(user, "race", None), d["race"]):
      failed.append("race")

  return failed


def main():
  with ConnectionPool(DB_URL, kwargs={"row_factory": dict_row, "autocommit": True}) as pool:
    repo = UserRepo(pool)
    service = UserService(repo) 
    print(repo.get_all_users())
    # use a student_id that exists in your database for testing
    student_id = "1234567"

    # --- read dealbreakers ---
    d = repo.get_dealbreaker(student_id)
    assert d, f"no dealbreakers found for {student_id}"
    print("Dealbreakers:", {k: v for k, v in d.items() if k not in ("created_at", "student_id")})

    # --- run the filter ---
    matches = repo.get_users_by_dealbreaker(student_id)
    match_ids = {u.student_id for u in matches}
    print(f"Filter returned {len(match_ids)} user(s): {sorted(match_ids)}")

    everyone = [u for u in repo.get_all_users() if u.student_id != student_id]
    print(f"Total other users in database: {len(everyone)}")

    if everyone and d.get("race") and not hasattr(everyone[0], "race"):
      print("WARNING: User has no 'race' attribute, so the race check can't pass for anyone.")

    # --- check 1: everyone returned passes every dealbreaker ---
    for u in matches:
      failed = violations(repo, u, d)
      assert not failed, f"{u.student_id} was returned but fails: {failed}"
    assert student_id not in match_ids, "requesting user should not appear in their own results"

    # --- check 2: everyone excluded fails at least one dealbreaker ---
    for u in everyone:
      if u.student_id not in match_ids:
        assert violations(repo, u, d), f"{u.student_id} was excluded but passes all dealbreakers"

    # --- check 3: service wrapper ---
    result = service.filter_users_by_dealbreaker(student_id)
    if match_ids:
      assert isinstance(result, Success), f"expected Success, got {result}"
    print("Service result:", type(result).__name__)

    print("\nAll checks passed.")
  
if __name__ == "__main__":
  main()