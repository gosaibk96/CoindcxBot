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
    return "CoinDCX Futures Supertrend Bot is Live!"

# =====================================================================
# ⚙️ COINDCX API CONFIGURATION & CREDS
# =====================================================================
API_KEY = "91bfc0639dea44d72c21aa63825d5baede1f38258d06a858"
API_SECRET = "d781e494887c9000273f2604225f84ce6c01822aae54be578963f5af99df00ee"

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

def check_futures_balance():
    time.sleep(3)
    # Corrected Futures balance endpoint path for CoinDCX derivatives/futures
    path = "/exchange/v1/derivatives/balances"
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
            print("💰 Futures Wallet Balances:", flush=True)
            print(f"   - Response: {balances}", flush=True)
        else:
            print(f"Futures Balance Error Status: {response.status_code}, Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error checking futures balance: {e}", flush=True)

def bot_loop():
    while True:
        check_futures_balance()
        fetch_live_prices()
        print("-" * 40, flush=True)
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
