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
    return "CoinDCX Connection Test is Live!"

# =====================================================================
# ⚙️ APNI NAYI BINA IP-RESTRICTION WALI COINDCX KEYS YAHAN DALIN
# =====================================================================
API_KEY = "91bfc0639dea44d72c21aa63825d5baede1f38258d06a858"
API_SECRET = "d781e494887c9000273f2604225f84ce6c01822aae54be578963f5af99df00ee"

BASE_URL = "https://api.coindcx.com"

def generate_coindcx_signature(secret_key, body_dict):
    secret_bytes = bytes(secret_key, encoding='utf-8')
    body_json = json.dumps(body_dict, separators=(',', ':'))
    signature = hmac.new(secret_bytes, body_json.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def check_balance():
    time.sleep(3)
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
        print("🔍 Checking CoinDCX Connection with New Key...", flush=True)
        response = requests.post(url, data=json.dumps(body), headers=headers, timeout=5)
        print(f"Response Status: {response.status_code}", flush=True)
        print(f"Response Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

if __name__ == "__main__":
    threading.Thread(target=check_balance).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
