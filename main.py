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
    return "CoinDCX Futures Bot is Live!"

# =====================================================================
# ⚙️ SETTINGS & CONFIGURATION
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

TRADE_PAIR = "B-XAU_USDT" 
DESIRED_INR_SIZE = 1000    # Aap yahan apna INR amount change kar sakte hain
TRADE_LEVERAGE = 10       
TRADE_SIDE = "buy"        
# =====================================================================

BASE_URL = "https://api.coindcx.com"
PUBLIC_URL = "https://public.coindcx.com"

def get_live_price(pair):
    try:
        url = PUBLIC_URL + "/exchange/ticker"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            tickers = response.json()
            for ticker in tickers:
                if ticker.get('market') == pair or ticker.get('symbol') == pair:
                    return float(ticker.get('last_price', 0))
        # Fallback to futures ticker if available
        url_fut = BASE_URL + "/exchange/v1/derivatives/futures/data/active_instruments"
        # Let's use public endpoint for current price
        res = requests.get("https://public.coindcx.com/market_data/trade_history?pair=" + pair, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                return float(data[0].get('price', 0))
    except Exception as e:
        print(f"❌ Error fetching price: {e}", flush=True)
    return None

def place_futures_order(pair, side, size_in_inr, leverage):
    # 1. Get current price to calculate correct quantity from INR
    print(f"🔍 Fetching live market price for {pair}...", flush=True)
    price = get_live_price(pair)
    
    if not price or price <= 0:
        print("❌ Could not fetch live price to calculate quantity!", flush=True)
        return

    # Assuming 1 USDT approx conversion or direct price mapping if quote is USDT
    # Calculating quantity based on INR size (Adjusting for USDT/INR if required by asset quote)
    calculated_quantity = round(size_in_inr / price, 4)
    if calculated_quantity <= 0:
        calculated_quantity = 0.001 # Minimum fallback
        
    print(f"📊 Live Price: {price} | Calculated Quantity for ₹{size_in_inr}: {calculated_quantity}", flush=True)

    path = "/exchange/v1/derivatives/futures/orders/create"
    url = BASE_URL + path
    
    body = {
        "timestamp": int(round(time.time() * 1000)),
        "order": {
            "side": side,
            "pair": pair,
            "order_type": "market_order",
            "total_quantity": calculated_quantity,
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
        print(f"🚀 Placing Futures Market Order for {pair} ({side.upper()})...", flush=True)
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        print(f"📦 Order Response Status: {response.status_code}", flush=True)
        print(f"📦 Order Response Body: {response.text}", flush=True)
    except Exception as e:
        print(f"❌ Error placing order: {e}", flush=True)

def bot_loop():
    time.sleep(3)
    place_futures_order(pair=TRADE_PAIR, side=TRADE_SIDE, size_in_inr=DESIRED_INR_SIZE, leverage=TRADE_LEVERAGE)
    
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
