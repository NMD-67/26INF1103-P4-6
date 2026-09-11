## auditor.py

inventory = 0

while True:
    user_input = input("Enter stock quantity: ").strip()
    
    # Check if user wants to quit
    if user_input.lower() == 'quit':
        break
