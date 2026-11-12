from app_logic import checkout

def handle_payment_request(user_id, total):
    print("API Request Received")
    return checkout(user_id, total)