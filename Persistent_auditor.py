inventory = 0
failed_entries = 0    # Count of rejected entries
deliveries_processed = 0  # Count of successful entries

print("=== Inventory Management System ===")
print("Enter stock quantities (type 'quit' to exit)\n")

def load_inventory():
    orders = []

    try:
        file = open("inventory.txt", "r")
        lines = file.readlines()

        for line in lines:
            line = line.strip()

            if line != "":
                parts = line.split(",")

                if len(parts) == 3:
                    order_id = int(parts[0])
                    product_name = parts[1]
                    quantity = int(parts[2])

                    orders.append([order_id, product_name, quantity])

        file.close()

    except FileNotFoundError:
        print("No inventory file found. Starting with empty inventory.")

    return orders

def save_inventory(orders):
    file = open("inventory.txt", "w")

    for order in orders:
        product_name = order[0]
        quantity = order[1]     
        file.write(product_name + "," + str(quantity) + "\n")

    file.close()
    print("Inventory successfully saved to inventory.txt")
    
def get_quantity():
    user_input = input("Enter quantity: ")

    if not user_input.isdigit():
        print("Error: Please enter a valid whole number.")
        return None

    quantity = int(user_input)

    if quantity < 0:
        print("Error: Negative numbers are not allowed.")
        return None

    return quantity

def get_product_name():
    name = input("Enter product name or type quit: ")

    if name.lower() == "quit":
        return "quit"

    if name.strip() == "":
        print("Error: Product name cannot be empty.")
        return None

    return name

# Function to process a delivery
def process_delivery(orders, product_name, quantity):
    orders.append([product_name, quantity])
    return orders



# Function to print the final report
def generate_report(total_orders, failed_attempts):
    print("\nFinal Report")
    print("Total Orders Processed:", total_orders)
    print("Number of Failed/Rejected Entries:", failed_attempts)


# Main program starts here

orders = load_inventory()
failed_entries = 0

print("Current Orders:")
for order in orders:
    print(order + ", " + str(order))

while True:
    product_name = get_product_name()

    if product_name == "quit":
        break

    if product_name is None:
        failed_entries = failed_entries + 1
        continue

    quantity = get_quantity()

    if quantity is None:
        failed_entries = failed_entries + 1
        continue

    orders = process_delivery(orders, product_name, quantity)

    print("\nNew Order Added:")
    print(product_name + "," + str(quantity))
    print()

save_inventory(orders)
generate_report(len(orders), failed_entries)
