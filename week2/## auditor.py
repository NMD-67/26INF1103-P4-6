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

    if quantity < 0:
        print("❌ Error: Negative values are not allowed.\n")
        failed_entries += 1
        continue

    inventory += quantity
    print(f"✓ Added {quantity} units. Current inventory: {inventory}\n")

    if inventory > 500:
        print("⚠️  ALERT: Inventory exceeds 500 units!")
        print(f"Current inventory: {inventory} units")
        print("Breaking loop due to overstock...\n")
        break

print("\n" + "="*40)
print("📊 FINAL REPORT")
print("="*40)
print(f"Total Units Processed: {inventory}")
print("="*40)
