def validate_user(user_id):
    check_db_connection()
    return True

def check_db_connection():
    log_status("DB alive")

def log_status(message):
    print(f"[LOG]: {message}")
print("Updating log...")
def checkout(user_id, amount):
    if validate_user(user_id):
        charge_card(amount)
        send_receipt(user_id)

def charge_card(amount):
    log_status("Card charged")

def send_receipt(user_id):
    log_status("Receipt sent")