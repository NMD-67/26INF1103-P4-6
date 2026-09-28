import database.db

def display_match(student, compatibility):
    print("\n" + "=" * 60)
    print("                    ✨ YOUR MATCH ✨")
    print("=" * 60)

    # Basic information
    print(f"\n  {student['name']}")
    print(f"  {student['gender']}  |  Year {student['year']}  |  {student['course']}")
    print(f"  MBTI: {student['mbti']}")

    # Compatibility
    print("\n" + "-" * 60)
    print(f"  💕 COMPATIBILITY: {compatibility}%")
    print("-" * 60)

    # Bio
    print("\n  📝 ABOUT")
    print(f"  {student['bio']}")

    # Interests
    print("\n  🎨 INTERESTS")
    print(f"  Hobbies:          {student['hobbies']}")
    print(f"  CCAs:             {student['ccas']}")
    print(f"  Interest Groups:  {student['interest_groups']}")
    print(f"  Events:           {student['events']}")

    # Matching information
    print("\n  💭 LOOKING FOR")
    print(f"  Here for:         {student['here_for']}")
    print(f"  Match preference: {student['match_preference']}")

    # Expectations
    print("\n  🤝 EXPECTATIONS")
    print(f"  {student['expectations']}")

    print("\n" + "=" * 60)
    print("       [A] Accept       [R] Reject       [N] Next")
    print("=" * 60)


current_match = 0



def parse_ai_matches(ai_output):
    lines = ai_output.strip().split("\n")
    matches = []

    for line in lines:
        if ":" in line and "%" in line:
            name_part, score_part = line.split(":")
            name = name_part.strip()
            score = int(score_part.strip().replace("%", ""))

            matches.append({
                "id": name,
                "score": score,
            })

    return matches

def load_matches():
    match_list = []
    try:
        file = open("Matching/Sample_score.txt", "r")
        lines = file.readlines()

        for line in lines:
            line = line.strip()

            if line != "":
                parts = line.split(":")

                if len(parts) == 2:
                    student_id = parts[0]
                    score = int(parts[1].replace("%", ""))

                    match_list.append([student_id, score])
        file.close()

    except FileNotFoundError:
        print("file not found")

    return match_list

def show_end_screen():
    print("No more matches available.")
    # Here you can implement the logic to display the end screen in your application.

def show_next_match(matches):
    global current_match

    if current_match >= len(matches):
        show_end_screen()
        return

    student_id, compatibility = matches[current_match]
    current_match += 1

    display_match(student_id, compatibility)

def update_db():
    # let raphael do (?)
    pass 

while current_match < len(load_matches()):
    show_next_match(load_matches())

    user_input = input("\nPress N to see the next match: ")

    if user_input.lower() != "n":
        print("Please press N to continue.")
