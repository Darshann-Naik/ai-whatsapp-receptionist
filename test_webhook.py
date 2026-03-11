import httpx
import json

# --- CONFIGURATION ---
# CRITICAL: This phone_number_id MUST exist in your local Postgres 'Tenant' table!
BUSINESS_PHONE_ID = "1234567890" 
CUSTOMER_PHONE = "919876543210"
MESSAGE_TEXT = "Hi! Do you have any scuba packages for tomorrow?"

def send_mock_webhook():
    print(f"🚀 Faking Meta Webhook from {CUSTOMER_PHONE}...")
    
    # The exact JSON structure Meta sends for a text message
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551111",
                                "phone_number_id": BUSINESS_PHONE_ID
                            },
                            "messages": [
                                {
                                    "from": CUSTOMER_PHONE,
                                    "id": "wamid.HBgLOTE...",
                                    "timestamp": "1663236053",
                                    "text": {
                                        "body": MESSAGE_TEXT
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    try:
        # Assuming your webhook route is at /api/v1/whatsapp/webhook
        # If your route is different, update this URL!
        response = httpx.post(
            "http://127.0.0.1:8000/api/v1/whatsapp/webhook", 
            json=payload,
            timeout=10.0
        )
        print(f"✅ Server responded with Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    send_mock_webhook()