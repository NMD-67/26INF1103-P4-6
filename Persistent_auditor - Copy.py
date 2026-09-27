# Function to load orders from file
def load_inventory():
    orders = []

    try:
        file = open("orders.txt", "r")
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


# Function to save orders to file
def save_inventory(orders):
    file = open("orders.txt", "w")

    for i in orders:
        file.write(str(i[0]) + "," + i[1] + "," + str(i[2]) + "\n")

    file.close()
    print("Inventory successfully saved to orders.txt")


# Function to get product name
def get_product_name():
    name = input("Enter product name or type quit: ")

    if name.lower() == "quit":
        return "quit"

    if name.strip() == "":
        print("Error: Product name cannot be empty.")
        return None

    return name

# Function to get quantity
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

# Function to add order
def process_delivery(orders, order_id, product_name, quantity):
    orders.append([order_id, product_name, quantity])
    return orders

# Function to calculate tax
def calculate_tax(amount):
    tax = amount * 0.10
    return tax

# Function to print final report
def generate_report(total_orders, failed_attempts):
    print("\nFinal Report")
    print("Total Orders Processed:", total_orders)
    for order in orders:
        print(str(order[0]) + ", " + order[1] + ", " + str(order[2]))
    print("Number of Failed/Rejected Entries:", failed_attempts)

# Main program
orders = load_inventory()
failed_entries = 0

# Decide starting ID
if len(orders) == 0:
    next_id = 1000
else:
    next_id = len(orders) + 1000

print("Current Orders:")
for order in orders:
    print(str(order[0]) + ", " + order[1] + ", " + str(order[2]))

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

    orders = process_delivery(orders, next_id, product_name, quantity)

    tax = calculate_tax(quantity)

    print("\nNew Order Added:")
    print(str(next_id) + "," + product_name + "," + str(quantity))
    print("Order successfully saved to orders.txt")
    print()

    next_id = next_id + 1

    save_inventory(orders)


generate_report(len(orders), failed_entries)