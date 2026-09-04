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
# ⚙️ SETTINGS & CONFIGURATION (Supertrend 10 / 1.5)
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

TRADE_PAIR = "B-ETH_USDT"
DESIRED_INR_SIZE = 2600
TRADE_LEVERAGE = 4
SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 
# =====================================================================

BASE_URL = "https://api.coindcx.com"

def get_live_price(pair):
    try:
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
        print(f"❌ Error fetching price for {pair}: {e}", flush=True)
    
    # Fallback default prices if API fails
    fallback_prices = {
        "B-ETH_USDT": 260000.0,
        "B-BTC_USDT": 7800000.0,
        "B-XAU_USDT": 4446.0
    }
    return fallback_prices.get(pair, 260000.0)

def get_candles(pair):
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval=1m&limit=50"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = data.get('data') or data.get('candles') or []
            return data
    except Exception as e:
        print(f"❌ Error fetching candles: {e}", flush=True)
    return None

def calculate_supertrend(candles):
    if not candles or not isinstance(candles, list) or len(candles) < SUPERTREND_PERIOD:
        return None, False, 0.0
    
    try:
        closes = []
        highs = []
        lows = []
        
        for c in candles:
            if isinstance(c, list):
                highs.append(float(c[2]))
                lows.append(float(c[3]))
                closes.append(float(c[4]))
            elif isinstance(c, dict):
                highs.append(float(c.get('high', 0)))
                lows.append(float(c.get('low', 0)))
                closes.append(float(c.get('close', 0)))
                
        if len(closes) < SUPERTREND_PERIOD:
            return None, False, 0.0

        current_close = closes[-1]
        prev_close = closes[-2]
        
        hl2 = (highs[-2] + lows[-2]) / 2
        atr = (highs[-2] - lows[-2]) 
        st_value = hl2 - (SUPERTREND_MULTIPLIER * atr)
        
        is_close_above = prev_close > st_value
        
        return st_value, is_close_above, current_close
    except Exception as e:
        print(f"❌ Calculation Error: {e}", flush=True)
        return None, False, 0.0

def place_order(pair, side, size_in_inr, leverage):
    print(f"🔍 Fetching live market price for {pair}...", flush=True)
    price = get_live_price(pair)
    
    if not price or price <= 0:
        price = 260000.0

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
    time.sleep(5)
    in_position = False
    
    while True:
        try:
            candles = get_candles(TRADE_PAIR)
            if candles:
                st_val, is_close_above, current_price = calculate_supertrend(candles)
                if st_val is not None:
                    print(f"📊 Price: {current_price} | Supertrend (10/1.5): {st_val} | In Position: {in_position}", flush=True)
                    
                    # ENTRY: Candle close above Supertrend
                    if not in_position and is_close_above:
                        print("🟢 Entry Condition Met: Candle closed above Supertrend!", flush=True)
                        place_order(TRADE_PAIR, "buy", DESIRED_INR_SIZE, TRADE_LEVERAGE)
                        in_position = True
                    
                    # EXIT / SL: Price crosses below Supertrend
                    elif in_position and current_price < st_val:
                        print("🔴 Exit Condition Met: Price crossed below Supertrend!", flush=True)
                        place_order(TRADE_PAIR, "sell", DESIRED_INR_SIZE, TRADE_LEVERAGE)
                        in_position = False
                else:
                    print("⚠️ Waiting for enough candle data...", flush=True)
            else:
                print("⚠️ Failed to fetch candles.", flush=True)
                    
        except Exception as e:
            print(f"❌ Loop Error: {e}", flush=True)
            
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
