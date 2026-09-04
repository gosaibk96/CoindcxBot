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
    return "CoinDCX Direct Futures Synchronized Supertrend Bot is Live!"

API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 

CUSTOM_SETTINGS = {
    "ETH": {"quantity": 0.02, "leverage": 10, "timeframe": "1m"}
}

BASE_URL = "https://api.coindcx.com"

def get_coin_config(coin_name):
    return CUSTOM_SETTINGS.get(coin_name, {"quantity": 0.02, "leverage": 10, "timeframe": "1m"})

def get_futures_candles(pair, timeframe):
    """ Direct Exchange Futures candles data jo chart se match kare """
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={timeframe}&limit=100"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = data.get('data') or data.get('candles') or []
            
            if data and isinstance(data, list):
                # Ensure data is sorted by timestamp oldest to newest
                # Format check: c[0] is usually timestamp
                try:
                    data = sorted(data, key=lambda x: x[0] if isinstance(x, list) else x.get('time', 0))
                except Exception:
                    pass
                return data
    except Exception as e:
        pass
    return None

def get_live_futures_price(pair):
    try:
        url = "https://public.coindcx.com/exchange/ticker"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            for item in res.json():
                market = item.get('market') or item.get('symbol')
                if market and pair.upper() in str(market).upper():
                    price = item.get('last_price') or item.get('price')
                    if price:
                        return float(price)
    except Exception as e:
        pass
    return 0.0

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

        # Standard Supertrend loop calculation over entire series to match TradingView precisely
        st_values = [0.0] * len(closes)
        direc = [1] * len(closes) # 1 for green/up, -1 for red/down
        
        hl2 = [(highs[i] + lows[i]) / 2 for i in range(len(closes))]
        atr = [highs[i] - lows[i] for i in range(len(closes))] # Simplified ATR approximation based on high-low or standard range

        # Basic Upper and Lower Bands
        basic_ub = [hl2[i] + (SUPERTREND_MULTIPLIER * atr[i]) for i in range(len(closes))]
        basic_lb = [hl2[i] - (SUPERTREND_MULTIPLIER * atr[i]) for i in range(len(closes))]
        
        final_ub = [0.0] * len(closes)
        final_lb = [0.0] * len(closes)
        
        for i in range(1, len(closes)):
            # Final Upper Band
            if basic_ub[i] < final_ub[i-1] or closes[i-1] > final_ub[i-1]:
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]
                
            # Final Lower Band
            if basic_lb[i] > final_lb[i-1] or closes[i-1] < final_lb[i-1]:
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]
                
            # Supertrend Line
            if i < SUPERTREND_PERIOD:
                continue
                
            if st_values[i-1] == final_ub[i-1] and closes[i] <= final_ub[i]:
                st_values[i] = final_ub[i]
                direc[i] = -1
            elif st_values[i-1] == final_ub[i-1] and closes[i] > final_ub[i]:
                st_values[i] = final_lb[i]
                direc[i] = 1
            elif st_values[i-1] == final_lb[i-1] and closes[i] >= final_lb[i]:
                st_values[i] = final_lb[i]
                direc[i] = 1
            elif st_values[i-1] == final_lb[i-1] and closes[i] < final_lb[i]:
                st_values[i] = final_ub[i]
                direc[i] = -1

        # Current and Previous indexes
        idx = len(closes) - 2 # Last closed candle
        prev_idx = len(closes) - 3 # Candle before last closed
        
        st_val = st_values[idx]
        is_green_prev = direc[idx] == 1
        is_green_pprev = direc[prev_idx] == 1
        
        is_red_to_green_flip = (not is_green_pprev) and is_green_prev
        is_green_to_red_flip = is_green_pprev and (not is_green_prev)
        
        current_close = closes[-1]
        prev_close = closes[idx]
        last_closed_time = timestamps[idx]

        return st_val, is_green_prev, is_red_to_green_flip, is_green_to_red_flip, current_close, prev_close, last_closed_time
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
    
    print(f"🤖 Synchronized Chart-Match Bot started for {coin_name}", flush=True)
    
    while True:
        try:
            config = get_coin_config(coin_name)
            candles = get_futures_candles(pair, config["timeframe"])
            
            if candles:
                st_val, is_green_prev, is_red_to_green_flip, is_green_to_red_flip, current_close, prev_close, candle_time = calculate_supertrend(candles)
                live_price = get_live_futures_price(pair)
                if live_price == 0:
                    live_price = current_close

                if st_val is not None and candle_time is not None:
                    trend_color = "GREEN" if is_green_prev else "RED"
                    pos_status = "BUY" if in_position else "NONE"
                    print(f"⚡ [{coin_name}] Live: {live_price} | PrevClose: {prev_close} | ST: {st_val:.2f} ({trend_color}) | R2G: {is_red_to_green_flip} | Pos: {pos_status}", flush=True)
                    
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
