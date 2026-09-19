inventory = 0
failed_entries = 0    # Count of rejected entries
deliveries_processed = 0  # Count of successful entries

print("=== Inventory Management System ===")
print("Enter stock quantities (type 'quit' to exit)\n")

def get_valid_input():
    user_input = input("Enter stock quantity or type quit: ")

    if user_input.lower() == "quit":
        return "quit"

    if not user_input.isdigit():
        print("Error: Please enter a valid whole number.")
        return None

    number = int(user_input)

    if number < 0:
        print("Error: Negative numbers are not allowed.")
        return None

    return number

# Function to process a delivery
def process_delivery(current_total, new_value):
    new_total = current_total + new_value
    return new_total

# Function to calculate tax
def calculate_tax(amount):
    tax = amount * 0.10
    return tax

# Function to print the final report
def generate_report(total_units, failed_attempts, deliveries_processed):
    print("\nFinal Report")
    print("Total Units Processed:", total_units)
    print("Total Deliveries Processed:", deliveries_processed)
    print("Number of Failed/Rejected Entries:", failed_attempts)

while True:
    value = get_valid_input()

    if value == "quit":
        break

    elif value is None:
        failed_entries = failed_entries + 1

    else:
        inventory = process_delivery(inventory, value)
        tax = calculate_tax(value)
        deliveries_processed = deliveries_processed + 1

        print("Delivery added:", value)
        print("Tax for this delivery:", tax)
        print("Current inventory total:", inventory)

        if inventory >= 500:
            print("OVERSTOCK ALERT: Total inventory has reached 500 units.")
            break

# Print final report when user quits
generate_report(inventory, failed_entries, deliveries_processed)
