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
    return "CoinDCX Supertrend Bot is Live!"

# =====================================================================
# ⚙️ COINDCX API CONFIGURATION & CREDS
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

BASE_URL = "https://api.coindcx.com"
PUBLIC_URL = "https://public.coindcx.com"
# =====================================================================

def fetch_live_prices():
    try:
        url = PUBLIC_URL + "/market_data/ticker"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            tickers = response.json()
            btc_price = "N/A"
            eth_price = "N/A"
            for item in tickers:
                if item.get('market') == 'BTCINR':
                    btc_price = item.get('last_price')
                elif item.get('market') == 'ETHINR':
                    eth_price = item.get('last_price')
            print(f"📈 Live Prices -> BTC: ₹{btc_price} | ETH: ₹{eth_price}", flush=True)
    except Exception as e:
        print(f"❌ Error fetching prices: {e}", flush=True)

def check_balance():
    time.sleep(3)
    path = "/exchange/v1/users/balances"
    url = BASE_URL + path
    
    body = {
        "timestamp": int(round(time.time() * 1000))
    }
    
    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(API_SECRET.encode('utf-8'), json_body.encode('utf-8'), hashlib.sha256).hexdigest()
    
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': API_KEY,
        'X-AUTH-SIGNATURE': signature
    }
    
    try:
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        if response.status_code == 200:
            balances = response.json()
            print("💰 Active Balances:", flush=True)
            for b in balances:
                # Sirf unhein print karega jinka balance ya locked balance 0 nahi hai
                if float(b.get('balance', 0)) > 0 or float(b.get('locked_balance', 0)) > 0:
                    print(f"   - {b['currency']}: Free = {b['balance']}, Locked = {b['locked_balance']}", flush=True)
        else:
            print(f"Balance Error Status: {response.status_code}, Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error checking balance: {e}", flush=True)

def bot_loop():
    while True:
        check_balance()
        fetch_live_prices()
        print("-" * 40, flush=True)
        time.sleep(60) # Har 1 minute mein update dikhayega

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
