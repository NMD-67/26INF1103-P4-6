import match
import database.db

load_matches()


print("Sorted Matches:")
for match in sorted_matches:
    print(f"{match['name']}: {match['score']}% - {match['label']}")