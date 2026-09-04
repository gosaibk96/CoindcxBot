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
    return "CoinDCX Multi-Coin Supertrend Bot is Live & Monitoring!"

# =====================================================================
# ⚙️ SETTINGS & CONFIGURATION
# =====================================================================
API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"

# All coins extracted from your screenshots added to the monitoring list
RAW_COINS = [
    "ROBO", "USUAL", "DRIFT", "CHILLGUY", "TRUTH", "RARE", "BLUAI", "GRIFFAIN", "XAN", "SENT",
    "W", "SIGN", "CTR", "GPS", "ACT", "MAV", "BABY", "COOKIE", "WOO",
    "BANANAS31", "BLESS", "AVAAI", "SXT", "MOCA", "PENGU", "BB", "MOVE", "SAHARA", "ARPA", "ZK",
    "BIGTIME", "VET", "FOGO", "INX", "1000XEC", "GMT", "XAI", "SWARMS", "ZORA", "PEOPLE",
    "BRETT", "SPACE", "ACH", "1000SHIB", "USTC", "ASTR", "HOME", "XNY", "ALT", "ROSE",
    "ANKR", "PUMP", "JASMY", "WAXP", "T", "MANTRA", "KAT", "ATH", "PIXEL", "TRIA",
    "REZ", "IOTX", "RVN", "1000BONK", "F", "FIGHT", "1000PEPE", "SKL", "G", "SOPH",
    "GALA", "1000CAT", "TOWNS", "LINEA", "TAC", "XVG", "ZIL", "ANIME", "SOLV", "GUN",
    "PTB", "ONE", "BOME", "TURBO", "XPIN", "CKB", "RSR", "TLM", "NOM", "BEAMX", "JCT",
    "HMSTR", "HOT", "1MBABYDOGE", "VTHO", "MEW", "NOT", "MEME", "IOST", "SLP", "TAG"
]

TRADE_PAIRS = [f"B-{coin}_USDT" for coin in RAW_COINS]

TIMEFRAME = "1m"            # ⏱️ Timeframe change kar sakte hain (jaise "1m", "3m", "5m", "15m")
DESIRED_INR_SIZE = 00        # Size set to 0 as requested
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
    return 1.0

def get_candles(pair):
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={TIMEFRAME}&limit=50"
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
    print(f"🔍 Fetching live market price for {pair}...", flush=True)
    price = get_live_price(pair)
    
    if not price or price <= 0:
        price = 1.0

    calculated_quantity = round(size_in_inr / price, 3) if size_in_inr > 0 else 0.0
        
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

def monitor_coin(pair):
    coin_name = pair.split('_')[0].replace('B-', '')
    in_position = False
    last_processed_candle = None
    startup_guard = 3  
    
    print(f"🤖 Monitoring started for {coin_name} on Timeframe: {TIMEFRAME}", flush=True)
    
    while True:
        try:
            candles = get_candles(pair)
            if candles:
                st_val, is_green, is_red_to_green_flip, current_price, candle_time = calculate_supertrend(candles)
                
                if st_val is not None:
                    pos_status = "BUY" if in_position else "NONE"
                    print(f"📊 {coin_name} Price: {current_price} | Supertrend: {st_val:.2f} | Position: {pos_status}", flush=True)
                    
                    if startup_guard > 0:
                        startup_guard -= 1
                        last_processed_candle = candle_time
                    else:
                        if candle_time and candle_time != last_processed_candle:
                            last_processed_candle = candle_time
                            
                            # ENTRY: Only buy if fresh Red-to-Green flip occurs on candle close
                            if not in_position and is_red_to_green_flip:
                                print(f"🟢 Condition Matched ({coin_name}): Supertrend flipped from Red to Green! Placing BUY order...", flush=True)
                                success = place_order(pair, "buy", DESIRED_INR_SIZE, TRADE_LEVERAGE)
                                if success:
                                    in_position = True
                            
                            # EXIT / SL: Price crosses below Supertrend
                            elif in_position and current_price < st_val:
                                print(f"🔴 Condition Matched ({coin_name}): Price crossed below Supertrend! Exiting position...", flush=True)
                                success = place_order(pair, "sell", DESIRED_INR_SIZE, TRADE_LEVERAGE)
                                if success:
                                    in_position = False
                        else:
                            if in_position and current_price < st_val:
                                print(f"🔴 Real-time SL Hit ({coin_name}): Price crossed below Supertrend! Exiting position...", flush=True)
                                success = place_order(pair, "sell", DESIRED_INR_SIZE, TRADE_LEVERAGE)
                                if success:
                                    in_position = False
            
        except Exception as e:
            print(f"❌ Loop Error for {coin_name}: {e}", flush=True)
            
        time.sleep(30)

def start_bot():
    time.sleep(5)
    for pair in TRADE_PAIRS:
        t = threading.Thread(target=monitor_coin, args=(pair,))
        t.daemon = True
        t.start()
        time.sleep(0.5)

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
