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
    return "CoinDCX Order Bot is Live!"

# =====================================================================
# ⚙️ SETTINGS & CONFIGURATION (Yahan se coin aur amount badal sakte hain)
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

TRADE_MARKET = "XAUUSDT"   # Yahan coin market likhein (jaise BTCINR, XAUUSDT)
TRADE_SIZE_INR = 1000       # Yahan se amount change kar sakte hain
# =====================================================================

BASE_URL = "https://api.coindcx.com"
PUBLIC_URL = "https://public.coindcx.com"

def place_order(market, side, size_in_inr):
    path = "/exchange/v1/orders/create"
    url = BASE_URL + path
    
    body = {
        "market": market,
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
        print(f"🚀 Placing Market Order for {market} ({side.upper()}) with Size ₹{size_in_inr}...", flush=True)
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        print(f"📦 Order Response Status: {response.status_code}", flush=True)
        print(f"📦 Order Response Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error placing order: {e}", flush=True)

def bot_loop():
    time.sleep(3)
    # Test order execution using configuration variables
    place_order(market=TRADE_MARKET, side="buy", size_in_inr=TRADE_SIZE_INR)
    
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
