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
    return "CoinDCX ETH Supertrend Bot is Live & Monitoring!"

# =====================================================================
# ⚙️ GLOBAL API SETTINGS
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 

# =====================================================================
# 🛠️ COIN SETTINGS (Filhal sirf ETH hai. Size mein apna amount daalein)
# =====================================================================
CUSTOM_SETTINGS = {
    "ETH": {"size": 2600, "leverage": 4, "timeframe": "1m"}
}

BASE_URL = "https://api.coindcx.com"

def get_coin_config(coin_name):
    if coin_name in CUSTOM_SETTINGS:
        return CUSTOM_SETTINGS[coin_name]
    return {"size": 0, "leverage": 10, "timeframe": "1m"}

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
    return 1.0

def get_candles(pair, timeframe):
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={timeframe}&limit=50"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = data.get('data') or data.get('candles') or []
            return data
    except Exception as e:
        print(f"❌ Error fetching candles for {pair}: {e}", flush=True)
    return None

def calculate_supertrend(candles):
    if not candles or not isinstance(candles, list) or len(candles) < SUPERTREND_PERIOD + 2:
        return None, False, False, 0.0, None
    
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
            return None, False, False, 0.0, None

        current_close = closes[-1]
        prev_close = closes[-2]
        prev_prev_close = closes[-3]
        current_candle_time = timestamps[-1]
        
        hl2_prev = (highs[-2] + lows[-2]) / 2
        atr_prev = highs[-2] - lows[-2]
        st_value_prev = hl2_prev - (SUPERTREND_MULTIPLIER * atr_prev)
        is_green_prev = prev_close > st_value_prev

        hl2_pprev = (highs[-3] + lows[-3]) / 2
        atr_pprev = highs[-3] - lows[-3]
        st_value_pprev = hl2_pprev - (SUPERTREND_MULTIPLIER * atr_pprev)
        is_green_pprev = prev_prev_close > st_value_pprev

        is_red_to_green_flip = (not is_green_pprev) and is_green_prev
        
        return st_value_prev, is_green_prev, is_red_to_green_flip, current_close, current_candle_time
    except Exception as e:
        print(f"❌ Calculation Error: {e}", flush=True)
        return None, False, False, 0.0, None

def place_order(pair, side, size_in_inr, leverage):
    if size_in_inr <= 0:
        print(f"ℹ️ Size is set to 0 for {pair}. Skipping live order placement.", flush=True)
        return True

    print(f"🔍 Fetching live market price for {pair}...", flush=True)
    price = get_live_price(pair)
    
    if not price or price <= 0:
        price = 1.0

    calculated_quantity = round(size_in_inr / price, 3)
        
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
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error placing order: {e}", flush=True)
        return False

def monitor_coin(coin_name):
    pair = f"B-{coin_name}_USDT"
    in_position = False
    last_processed_candle = None
    startup_guard = 3  
    
    print(f"🤖 Monitoring started for {coin_name}", flush=True)
    
    while True:
        try:
            config = get_coin_config(coin_name)
            current_timeframe = config["timeframe"]
            current_size = config["size"]
            current_leverage = config["leverage"]

            candles = get_candles(pair, current_timeframe)
            if candles:
                st_val, is_green, is_red_to_green_flip, current_price, candle_time = calculate_supertrend(candles)
                
                if st_val is not None:
                    pos_status = "BUY" if in_position else "NONE"
                    print(f"📊 [{coin_name} | TF: {current_timeframe} | Size: ₹{current_size}] Price: {current_price} | ST: {st_val:.2f} | Pos: {pos_status}", flush=True)
                    
                    if startup_guard > 0:
                        startup_guard -= 1
                        last_processed_candle = candle_time
                    else:
                        if candle_time and candle_time != last_processed_candle:
                            last_processed_candle = candle_time
                            
                            if not in_position and is_red_to_green_flip:
                                print(f"🟢 Condition Matched ({coin_name}): Red to Green Flip! Placing BUY...", flush=True)
                                success = place_order(pair, "buy", current_size, current_leverage)
                                if success:
                                    in_position = True
                            
                            elif in_position and current_price < st_val:
                                print(f"🔴 Condition Matched ({coin_name}): Price below Supertrend! Exiting...", flush=True)
                                success = place_order(pair, "sell", current_size, current_leverage)
                                if success:
                                    in_position = False
                        else:
                            if in_position and current_price < st_val:
                                print(f"🔴 Real-time SL Hit ({coin_name})! Exiting...", flush=True)
                                success = place_order(pair, "sell", current_size, current_leverage)
                                if success:
                                    in_position = False
            
        except Exception as e:
            print(f"❌ Loop Error for {coin_name}: {e}", flush=True)
            
        time.sleep(30)

def start_bot():
    time.sleep(5)
    for coin in CUSTOM_SETTINGS.keys():
        t = threading.Thread(target=monitor_coin, args=(coin,))
        t.daemon = True
        t.start()
        time.sleep(0.3)

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
