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
    return "CoinDCX Futures Order Bot is Live!"

# =====================================================================
# ⚙️ SETTINGS & CONFIGURATION (Yahan se aap amount aur coin badal sakte hain)
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

TRADE_PAIR = "XAUUSDT"    # Jiss coin mein trade karni ho uska pair yahan likhein
TRADE_SIZE_INR = 1000      # Yahan se amount change kar sakte hain (jaise 700, 1000, etc.)
# =====================================================================

BASE_URL = "https://api.coindcx.com"
PUBLIC_URL = "https://public.coindcx.com"

def check_futures_wallet():
    path = "/exchange/v1/derivatives/futures/wallets"
    url = BASE_URL + path
    body = {"timestamp": int(round(time.time() * 1000))}
    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(API_SECRET.encode('utf-8'), json_body.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-SIGNATURE': signature}
    
    try:
        response = requests.get(url, data=json_body, headers=headers, timeout=5)
        if response.status_code == 200:
            balances = response.json()
            for b in balances:
                if b.get('currency_short_name') == 'INR':
                    print(f"💰 Futures Wallet INR -> Free: {b.get('balance')}, Locked: {b.get('locked_balance')}", flush=True)
    except Exception as e:
        print(f"❌ Error checking wallet: {e}", flush=True)

def place_futures_order(pair, side, size_in_inr):
    path = "/exchange/v1/derivatives/futures/orders/create"
    url = BASE_URL + path
    
    body = {
        "pair": pair,
        "side": side,
        "order_type": "market_order",
        "total_quantity": size_in_inr,
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
        print(f"🚀 Placing Market Order for {pair} ({side.upper()}) with Size ₹{size_in_inr}...", flush=True)
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        print(f"📦 Order Response Status: {response.status_code}", flush=True)
        print(f"📦 Order Response Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error placing order: {e}", flush=True)

def bot_loop():
    time.sleep(3)
    check_futures_wallet()
    
    # Yahan upar define kiye gaye variables use ho rahe hain
    place_futures_order(pair=TRADE_PAIR, side="buy", size_in_inr=TRADE_SIZE_INR)
    
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
