from logic import compatibility_label, parse_ai_matches, sort_matches

ai_output = """
Aidan: 70%
Bryan: 60%
Chris: 43%
Daniel: 80%
Ethan: 94%
Fabian: 70%
"""

matches = parse_ai_matches(ai_output)
sorted_matches = sort_matches(matches)

print("Sorted Matches:")
for match in sorted_matches:
    print(f"{match['name']}: {match['score']}% - {match['label']}")