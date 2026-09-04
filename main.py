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
DESIRED_INR_SIZE = 1000    # Aapka fixed investment size in INR (₹700)
TRADE_LEVERAGE = 10       
TRADE_SIDE = "buy"        # "buy" ya "sell"
# =====================================================================

BASE_URL = "https://api.coindcx.com"

def get_live_price(pair):
    try:
        # Method 1: Fetching from Futures Active Instruments endpoint (Most accurate for futures)
        url = BASE_URL + "/exchange/v1/derivatives/futures/data/active_instruments"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            instruments = response.json()
            for inst in instruments:
                # Check different possible keys for instrument name/symbol
                name = inst.get('pair') or inst.get('coindcx_name') or inst.get('symbol')
                if name and pair.upper() in str(name).upper():
                    price = inst.get('last_price') or inst.get('price') or inst.get('mark_price')
                    if price:
                        return float(price)
        
        # Method 2: Public Ticker Fallback
        url_public = "https://public.coindcx.com/exchange/ticker"
        res = requests.get(url_public, timeout=5)
        if res.status_code == 200:
            tickers = res.json()
            for ticker in tickers:
                market_val = ticker.get('market') or ticker.get('symbol')
                if market_val and pair.upper() in str(market_val).upper():
                    price = ticker.get('last_price') or ticker.get('price')
                    if price:
                        return float(price)
    except Exception as e:
        print(f"❌ Error fetching price: {e}", flush=True)
    
    # Ultimate Safe Fallback Price based on recent market data
    print("⚠️ Using fallback market price.", flush=True)
    return 4446.0

def place_futures_order(pair, side, size_in_inr, leverage):
    print(f"🔍 Fetching live market price for {pair}...", flush=True)
    price = get_live_price(pair)
    
    if not price or price <= 0:
        price = 4446.0

    # Automatically calculates quantity based on INR size and rounds to 3 decimals
    calculated_quantity = round(size_in_inr / price, 3)
    if calculated_quantity <= 0:
        calculated_quantity = 0.001
        
    print(f"📊 Live Price: {price} | Target INR: ₹{size_in_inr} | Calculated Qty: {calculated_quantity}", flush=True)

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
            "margin_currency_short_name": "INR", 
            "notification": "email_notification",
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
