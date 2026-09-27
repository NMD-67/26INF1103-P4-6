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

orders = load_inventory()
print(orders)