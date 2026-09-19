inventory = 0
total_processed = 0  # Count of successful entries
failed_entries = 0    # Count of rejected entries

print("=== Inventory Management System ===")
print("Enter stock quantities (type 'quit' to exit)\n")

def get_valid_input():
    while True:
        user_input = input("Enter stock quantity: ").strip()
        
        # Check if user wants to quit
        if user_input.lower() == 'quit':
            break
    
    if not user_input.isdigit() and not (user_input.startswith('-') and user_input[1:].isdigit()):
        print("❌ Error: Please enter a valid number.\n")
        failed_entries += 1
        continue
    
    # Convert to integer
    quantity = int(user_input)
    
    # 5. Reject negative numbers
    if quantity < 0:
        print("❌ Error: Negative values are not allowed.\n")
        failed_entries += 1
        continue
    
    # 6. Update inventory (valid entry)
    inventory += quantity
    total_processed += 1
    print(f"✓ Added {quantity} units. Current inventory: {inventory}\n")
    
    # 7. Check for overstock (exceeds 500)
    if inventory > 500:
        print("⚠️  ALERT: Inventory exceeds 500 units!")
        print(f"Current inventory: {inventory} units")
        print("Breaking loop due to overstock...\n")
        break
def process_delivery(current_total, new_value):
    return current_total + new_value

def calculate_tax(amount)
    tax_rate = 0.1 
    return amount * tax_rate


print("\n" + "="*40)
print("📊 FINAL REPORT")
print("="*40)
print(f"Total Units Processed: {inventory}")
print(f"Number of Failed/Rejected Entries: {failed_entries}")
print(f"Successful Entries: {total_processed}")
print("="*40)