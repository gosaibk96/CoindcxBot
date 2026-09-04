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
    return "CoinDCX Futures Direct Feed Supertrend Bot is Live!"

API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 

CUSTOM_SETTINGS = {
    "ETH": {"quantity": 0.02, "leverage": 4, "timeframe": "1m"}
}

BASE_URL = "https://api.coindcx.com"

def get_coin_config(coin_name):
    return CUSTOM_SETTINGS.get(coin_name, {"quantity": 0.02, "leverage": 10, "timeframe": "1m"})

def get_live_futures_price(pair):
    """ Direct CoinDCX Futures market live price fetch karne ke liye """
    try:
        url = "https://public.coindcx.com/exchange/ticker"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            for item in res.json():
                market = item.get('market') or item.get('symbol')
                # Futures contracts ke liye 'B-ETH_USDT' ya similar format match karte hain
                if market and pair.upper() in str(market).upper():
                    price = item.get('last_price') or item.get('price')
                    if price:
                        return float(price)
    except Exception as e:
        pass
    
    # Fallback: Agar futures ticker me na mile toh derivatives exchange endpoint try karo
    try:
        url_deriv = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments"
        res = requests.get(url_deriv, timeout=3)
        if res.status_code == 200:
            for inst in res.json():
                if inst.get('pair') == pair:
                    return float(inst.get('last_price', 0))
    except Exception as e:
        pass
        
    return 0.0

def get_candles(pair, timeframe):
    try:
        # Futures market data candles endpoint
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
        return None, False, False, False, 0.0, 0.0, None
    
    try:
        closes = []
        highs = []
        lows = []
        timestamps = []
        
        for c in candles:
            if isinstance(c, list):
                timestamps.append(c[0])
                highs.append(float(c[2]))
                lows.append(float(c[3]))
                closes.append(float(c[4]))
            elif isinstance(c, dict):
                timestamps.append(c.get('time', 0))
                highs.append(float(c.get('high', 0)))
                lows.append(float(c.get('low', 0)))
                closes.append(float(c.get('close', 0)))
                
        if len(closes) < SUPERTREND_PERIOD + 2:
            return None, False, False, False, 0.0, 0.0, None

        prev_close = closes[-2]
        prev_prev_close = closes[-3]
        current_close = closes[-1]
        last_closed_candle_time = timestamps[-2]

        # Previous closed candle Supertrend (-2)
        hl2_prev = (highs[-2] + lows[-2]) / 2
        atr_prev = highs[-2] - lows[-2]
        st_value_prev = hl2_prev - (SUPERTREND_MULTIPLIER * atr_prev)
        is_green_prev = prev_close > st_value_prev

        # Candle before previous Supertrend (-3)
        hl2_pprev = (highs[-3] + lows[-3]) / 2
        atr_pprev = highs[-3] - lows[-3]
        st_value_pprev = hl2_pprev - (SUPERTREND_MULTIPLIER * atr_pprev)
        is_green_pprev = prev_prev_close > st_value_pprev

        # Strict Red to Green Crossover on Close
        is_red_to_green_flip = (not is_green_pprev) and is_green_prev

        # Strict Green to Red Crossover on Close
        is_green_to_red_flip = is_green_pprev and (not is_green_prev)
        
        return st_value_prev, is_green_prev, is_red_to_green_flip, is_green_to_red_flip, current_close, prev_close, last_closed_candle_time
    except Exception as e:
        return None, False, False, False, 0.0, 0.0, None

def place_order(pair, side, quantity, leverage):
    if quantity <= 0:
        return True

    print(f"📊 Placing Futures Order -> Side: {side.upper()} | Qty: {quantity} | Leverage: {leverage}x", flush=True)

    path = "/exchange/v1/derivatives/futures/orders/create"
    url = BASE_URL + path
    
    body = {
        "timestamp": int(round(time.time() * 1000)),
        "order": {
            "side": side,
            "pair": pair,
            "order_type": "market_order",
            "total_quantity": quantity,
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
    last_processed_time = None 
    
    print(f"🤖 Futures Direct-Feed Bot started for {coin_name}", flush=True)
    
    while True:
        try:
            config = get_coin_config(coin_name)
            candles = get_candles(pair, config["timeframe"])
            
            if candles:
                st_val, is_green_prev, is_red_to_green_flip, is_green_to_red_flip, current_close, prev_close, candle_time = calculate_supertrend(candles)
                live_price = get_live_futures_price(pair)
                if live_price == 0:
                    live_price = current_close

                if st_val is not None and candle_time is not None:
                    pos_status = "BUY" if in_position else "NONE"
                    print(f"⚡ [{coin_name}] Futures Live: {live_price} | PrevClose: {prev_close} | ST: {st_val:.2f} | R2G: {is_red_to_green_flip} | Pos: {pos_status}", flush=True)
                    
                    if candle_time != last_processed_time:
                        # ENTRY: Red se Green flip hone par candle close hone par
                        if not in_position and is_red_to_green_flip:
                            print(f"🟢 Candle Closed Above Red ST! Placing BUY...", flush=True)
                            if place_order(pair, "buy", config["quantity"], config["leverage"]):
                                in_position = True
                                last_processed_time = candle_time
                        
                        # EXIT: Green se Red flip hone par candle close hone par
                        elif in_position and is_green_to_red_flip:
                            print(f"🔴 Candle Closed Below Green ST! Placing SELL (Exit)...", flush=True)
                            if place_order(pair, "sell", config["quantity"], config["leverage"]):
                                in_position = False
                                last_processed_time = candle_time
                        
                        else:
                            last_processed_time = candle_time
            
        except Exception as e:
            print(f"❌ Loop Error: {e}", flush=True)
            
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
