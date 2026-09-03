import time
import hmac
import hashlib
import requests
import json
import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "CoinDCX Trading Bot is Live!"

# =====================================================================
# ⚙️ COINDCX API CONFIGURATION & CREDS
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

BASE_URL = "https://api.coindcx.com"
# =====================================================================

def generate_coindcx_signature(secret_key, body_dict):
    secret_bytes = bytes(secret_key, encoding='utf-8')
    body_json = json.dumps(body_dict, separators=(',', ':'))
    signature = hmac.new(secret_bytes, body_json.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def check_balance():
    time.sleep(2)  # Wait for server to stabilize
    path = "/exchange/v1/users/balances"
    url = BASE_URL + path
    
    body = {
        "timestamp": int(round(time.time() * 1000))
    }
    
    signature = generate_coindcx_signature(API_SECRET, body)
    
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': API_KEY,
        'X-AUTH-SIGNATURE': signature
    }
    
    try:
        print("🔍 Checking CoinDCX Balance...", flush=True)
        response = requests.post(url, data=json.dumps(body), headers=headers, timeout=5)
        print("Response Status:", response.status_code, flush=True)
        print("Response Body:", response.text, flush=True)
    except Exception as e:
        print(f"❌ Error checking balance: {e}", flush=True)

if __name__ == "__main__":
    # Run balance check in a separate background thread
    threading.Thread(target=check_balance).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
