inventory = 0
total_processed = 0  # Count of successful entries
failed_entries = 0    # Count of rejected entries

print("=== Inventory Management System ===")
print("Enter stock quantities (type 'quit' to exit)\n")

def get_valid_input():
    while True:
        user_input = input("Enter stock quantity (or type 'quit' to exit): ").strip()

        if user_input.lower() == "quit":
            return "quit"

        if not user_input.isdigit() and not (user_input.startswith("-") and user_input[1:].isdigit()):
            print("Error: Invalid input. Please enter a whole number.")
            continue

        value = int(user_input)

        if value < 0:
            print("Error: Negative numbers are not allowed.")
            continue

        return value

def process_delivery(current_total, new_value):
    return current_total + new_value

def calculate_tax(amount):
    return amount * 0.10

def generate_report(total_units, failed_attempts, deliveries_processed):
    print("\n=== Final Report ===")
    print(f"Total Units Processed: {total_units}")
    print(f"Total Deliveries Processed: {deliveries_processed}")
    print(f"Number of Failed/Rejected Entries: {failed_attempts}")
