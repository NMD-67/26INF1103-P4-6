def compatibility_label(score):
    if 85 <= score <= 100:
        return "High Compatibility"
    elif 70 <= score <= 84:
        return "Moderate Compatibility"
    elif 0 <= score < 70:
        return "Low Compatibility"
    else:
        return "Invalid score"

def parse_ai_matches(ai_output):
    lines = ai_output.strip().split("\n")
    matches = []

    for line in lines:
        if ":" in line and "%" in line:
            name_part, score_part = line.split(":")
            name = name_part.strip()
            score = int(score_part.strip().replace("%", ""))

            matches.append({
                "name": name,
                "score": score,
                "label": compatibility_label(score)
            })

    return matches

def sort_matches(matches):
    return sorted(matches, key=lambda x: x["score"], reverse=True)