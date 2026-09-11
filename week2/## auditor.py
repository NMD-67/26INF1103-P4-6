## auditor.py

inventory = 0

print("=== Inventory Management System ===")
print("Enter stock quantities (type 'quit' to exit)\n")

while True:
    user_input = input("Enter stock quantity: ").strip()
    
    # Check if user wants to quit
    if user_input.lower() == 'quit':
        break

    if not user_input.isdigit() and not (user_input.startswith('-') and user_input[1:].isdigit()):
        print("❌ Error: Please enter a valid number.\n")
        continue
    quantity = int(user_input)
    