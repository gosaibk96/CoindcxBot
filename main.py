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
    return "CoinDCX ETH Supertrend Fast Bot is Live!"

API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 

CUSTOM_SETTINGS = {
    "ETH": {"size": 2600, "leverage": 4, "timeframe": "1m"}
}

BASE_URL = "https://api.coindcx.com"

def get_coin_config(coin_name):
    return CUSTOM_SETTINGS.get(coin_name, {"size": 0, "leverage": 10, "timeframe": "1m"})

def get_live_price(pair):
    try:
        url_public = "https://public.coindcx.com/exchange/ticker"
        res = requests.get(url_public, timeout=3)
        if res.status_code == 200:
            for ticker in res.json():
                market_val = ticker.get('market') or ticker.get('symbol')
                if market_val and pair.upper() in str(market_val).upper():
                    price = ticker.get('last_price') or ticker.get('price')
                    if price:
                        return float(price)
    except Exception as e:
        pass
    return 0.0

def get_candles(pair, timeframe):
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={timeframe}&limit=50"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = data.get('data') or data.get('candles') or []
            return data
    except Exception as e:
        pass
    return None

def calculate_supertrend(candles):
    if not candles or len(candles) < SUPERTREND_PERIOD + 2:
        return None, False, 0.0, 0.0
    
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
                
        if len(closes) < SUPERTREND_PERIOD + 2:
            return None, False, 0.0, 0.0

        current_close = closes[-1]
        hl2 = (highs[-2] + lows[-2]) / 2
        atr = highs[-2] - lows[-2]
        st_value = hl2 - (SUPERTREND_MULTIPLIER * atr)
        
        is_green = current_close > st_value
        return st_value, is_green, current_close, st_value
    except Exception as e:
        return None, False, 0.0, 0.0

def place_order(pair, side, size_in_inr, leverage):
    if size_in_inr <= 0:
        return True

    price = get_live_price(pair)
    if not price or price <= 0:
        price = 1.0

    calculated_quantity = round(size_in_inr / price, 3)
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
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        print(f"📦 Order Status: {response.status_code} | Body: {response.text}", flush=True)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Order Error: {e}", flush=True)
        return False

def monitor_coin(coin_name):
    pair = f"B-{coin_name}_USDT"
    in_position = False
    
    print(f"🤖 Fast Monitoring started for {coin_name}", flush=True)
    
    while True:
        try:
            config = get_coin_config(coin_name)
            candles = get_candles(pair, config["timeframe"])
            
            if candles:
                st_val, is_green, current_close, _ = calculate_supertrend(candles)
                live_price = get_live_price(pair)
                if live_price == 0:
                    live_price = current_close

                if st_val is not None:
                    print(f"⚡ [{coin_name}] LivePrice: {live_price} | ST: {st_val:.2f} | Green: {is_green} | Pos: {in_position}", flush=True)
                    
                    # Direct execution: Jaise hi price Supertrend ke upar ho aur position na ho
                    if not in_position and is_green:
                        print(f"🟢 Fast Entry Triggered! Placing BUY...", flush=True)
                        if place_order(pair, "buy", config["size"], config["leverage"]):
                            in_position = True
                    
                    # Exit: Jab price Supertrend ke neeche jaye
                    elif in_position and not is_green:
                        print(f"🔴 Fast Exit Triggered! Placing SELL...", flush=True)
                        if place_order(pair, "sell", config["size"], config["leverage"]):
                            in_position = False
            
        except Exception as e:
            print(f"❌ Loop Error: {e}", flush=True)
            
        # Fast check every 3 seconds instead of 30 seconds
        time.sleep(3)

def start_bot():
    time.sleep(2)
    for coin in CUSTOM_SETTINGS.keys():
        t = threading.Thread(target=monitor_coin, args=(coin,))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
