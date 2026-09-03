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
# ⚙️ SETTINGS & CONFIGURATION (Yahan se aap sab kuch change kar sakte hain)
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

TRADE_PAIR = "XAUUSDT"    # Coin pair (jaise XAUUSDT)
TRADE_SIZE = 1000          # Quantity / Amount
TRADE_LEVERAGE = 4        # Leverage (jaise 4x ke liye 4)
TRADE_SIDE = "buy"        # "buy" (Long) ya "sell" (Short)
# =====================================================================

BASE_URL = "https://api.coindcx.com"

def place_futures_order(pair, side, total_quantity, leverage):
    path = "/exchange/v1/derivatives/futures/orders/create"
    url = BASE_URL + path
    
    body = {
        "timestamp": int(round(time.time() * 1000)),
        "order": {
            "side": side,
            "pair": pair,
            "order_type": "market_order",
            "total_quantity": total_quantity,
            "leverage": leverage,
            "notification": "email_notification",
            "time_in_force": "good_till_cancel",
            "hidden": False,
            "post_only": False
        }
    }
    
    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(API_SECRET.encode('utf-8'), json_body.encode('utf-8'), hashlib.sha256).hexdigest()
    
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': API_KEY,
        'X-AUTH-SIGNATURE': signature
    }
    
    try:
        print(f"🚀 Placing Futures Market Order for {pair} ({side.upper()}) | Size: {total_quantity} | Leverage: {leverage}x...", flush=True)
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        print(f"📦 Order Response Status: {response.status_code}", flush=True)
        print(f"📦 Order Response Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error placing order: {e}", flush=True)

def bot_loop():
    time.sleep(3)
    # Order execution using configuration variables
    place_futures_order(pair=TRADE_PAIR, side=TRADE_SIDE, total_quantity=TRADE_SIZE, leverage=TRADE_LEVERAGE)
    
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
