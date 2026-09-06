import time
import hmac
import hashlib
import requests
import json
import os
import threading
from flask import Flask

app = Flask(__name__)

STATS = {}

CUSTOM_SETTINGS = {
    "1000PEPE": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "PUMP": {"quantity": 1600.0, "leverage": 2, "timeframe": "1h"},
    "TRIA": {"quantity": 1400.0, "leverage": 2, "timeframe": "1h"},
    "PENGU": {"quantity": 700.0, "leverage": 2, "timeframe": "1h"},
    "1000SHIB": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "1000BONK": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "ANKR": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "JASMY": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "ZORA": {"quantity": 750.0, "leverage": 2, "timeframe": "1h"},
    "PEOPLE": {"quantity": 750.0, "leverage": 2, "timeframe": "1h"},
    "MOVE": {"quantity": 700.0, "leverage": 2, "timeframe": "1h"},
    "CHILLGUY": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "BRETT": {"quantity": 1100.0, "leverage": 2, "timeframe": "1h"},
    "MANTRA": {"quantity": 1400.0, "leverage": 2, "timeframe": "1h"},
    "VET": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "GMT": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "ROSE": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "IOTX": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "WOO": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "ACT": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "USUAL": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "DRIFT": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "TRUTH": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "WAXP": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "SIGN": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "BIGTIME": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "RARE": {"quantity": 500.0, "leverage": 2, "timeframe": "1h"},
    "GRIFFAIN": {"quantity": 500.0, "leverage": 2, "timeframe": "1h"},
    "BLUAI": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"},
    "REZ": {"quantity": 0.0, "leverage": 10, "timeframe": "1m"}
}

for coin in CUSTOM_SETTINGS.keys():
    STATS[coin] = {
        "total_trades": 0, "wins": 0, "losses": 0, "pnl": 0.0,
        "status": "MONITORING"
    }

@app.route('/')
def dashboard():
    html = """
    <html>
    <head>
        <title>Bot Performance Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { font-family: Arial, sans-serif; background: #121212; color: #fff; padding: 20px; }
            h2 { color: #00ffcc; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #333; padding: 10px; text-align: center; }
            th { background: #1f1f1f; color: #00ffcc; }
            tr:nth-child(even) { background: #1a1a1a; }
            .win { color: #00ff00; font-weight: bold; }
            .loss { color: #ff4d4d; font-weight: bold; }
            .monitoring { color: #b3b3b3; }
            .in-trade { color: #00ffcc; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>🚀 Strategy Performance Dashboard</h2>
        <p>Auto-refreshing every 5 seconds...</p>
        <table>
            <tr>
                <th>Coin Name</th>
                <th>Status</th>
                <th>Total Trades</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Win Rate (%)</th>
                <th>Total PnL (INR)</th>
            </tr>
    """
    for coin, data in STATS.items():
        win_rate = (data["wins"] / data["total_trades"] * 100) if data["total_trades"] > 0 else 0.0
        pnl_class = "win" if data["pnl"] >= 0 else "loss"
        status_class = "in-trade" if data["status"] == "IN_TRADE" else "monitoring"
        html += f"""
            <tr>
                <td><b>{coin}</b></td>
                <td class="{status_class}">{data['status']}</td>
                <td>{data['total_trades']}</td>
                <td style="color: #00ff00;">{data['wins']}</td>
                <td style="color: #ff4d4d;">{data['losses']}</td>
                <td>{win_rate:.2f}%</td>
                <td class="{pnl_class}">{data['pnl']:.2f}</td>
            </tr>
        """
    html += """
        </table>
    </body>
    </html>
    """
    return html

API_KEY = "13b49b25afb4db3558c3a164740bdbaaf365e93bdf63aff6"
API_SECRET = "443c5865cda7332aced28532f7593ccf43fa754179bef484fbbea2198777cfb2"
SUPERTREND_PERIOD = 10      
SUPERTREND_MULTIPLIER = 1.5 
BASE_URL = "https://api.coindcx.com"

def get_futures_candles(pair, timeframe):
    try:
        url = f"https://public.coindcx.com/market_data/candles?pair={pair}&interval={timeframe}&limit=100"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = data.get('data') or data.get('candles') or []
            if data and isinstance(data, list):
                try:
                    data = sorted(data, key=lambda x: x[0] if isinstance(x, list) else x.get('time', 0))
                except Exception:
                    pass
                return data
    except Exception:
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
    except Exception:
        pass
    return 0.0

def calculate_supertrend(candles):
    if not candles or len(candles) < SUPERTREND_PERIOD + 5:
        return None, None, False, False, 0.0, 0.0, None
    try:
        closes, highs, lows, timestamps = [], [], [], []
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
                
        length = len(closes)
        if length < SUPERTREND_PERIOD + 5:
            return None, None, False, False, 0.0, 0.0, None

        tr = [0.0] * length
        tr[0] = highs[0] - lows[0]
        for i in range(1, length):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))

        atr = [0.0] * length
        atr[SUPERTREND_PERIOD] = sum(tr[1:SUPERTREND_PERIOD+1]) / SUPERTREND_PERIOD
        for i in range(SUPERTREND_PERIOD + 1, length):
            atr[i] = (atr[i-1] * (SUPERTREND_PERIOD - 1) + tr[i]) / SUPERTREND_PERIOD

        st_values = [0.0] * length
        direc = [1] * length 
        hl2 = [(highs[i] + lows[i]) / 2 for i in range(length)]
        basic_ub = [hl2[i] + (SUPERTREND_MULTIPLIER * atr[i]) for i in range(length)]
        basic_lb = [hl2[i] - (SUPERTREND_MULTIPLIER * atr[i]) for i in range(length)]
        
        final_ub = [0.0] * length
        final_lb = [0.0] * length
        
        for i in range(SUPERTREND_PERIOD, length):
            final_ub[i] = basic_ub[i] if basic_ub[i] < final_ub[i-1] or closes[i-1] > final_ub[i-1] else final_ub[i-1]
            final_lb[i] = basic_lb[i] if basic_lb[i] > final_lb[i-1] or closes[i-1] < final_lb[i-1] else final_lb[i-1]
                
            if i == SUPERTREND_PERIOD:
                st_values[i] = final_ub[i]
                continue
                
            if st_values[i-1] == final_ub[i-1] and closes[i] <= final_ub[i]:
                st_values[i] = final_ub[i]; direc[i] = -1
            elif st_values[i-1] == final_ub[i-1] and closes[i] > final_ub[i]:
                st_values[i] = final_lb[i]; direc[i] = 1
            elif st_values[i-1] == final_lb[i-1] and closes[i] >= final_lb[i]:
                st_values[i] = final_lb[i]; direc[i] = 1
            elif st_values[i-1] == final_lb[i-1] and closes[i] < final_lb[i]:
                st_values[i] = final_ub[i]; direc[i] = -1

        idx = length - 2 
        prev_idx = length - 3 
        st_val = st_values[idx]
        current_st = st_values[-1]
        is_green_prev = direc[idx] == 1
        is_green_pprev = direc[prev_idx] == 1
        is_red_to_green_flip = (not is_green_pprev) and is_green_prev
        
        return st_val, current_st, is_green_prev, is_red_to_green_flip, closes[-1], closes[idx], timestamps[idx]
    except Exception:
        return None, None, False, False, 0.0, 0.0, None

def place_order(pair, side, quantity, leverage):
    if quantity <= 0:
        return True 
    path = "/exchange/v1/derivatives/futures/orders/create"
    url = BASE_URL + path
    body = {
        "timestamp": int(round(time.time() * 1000)),
        "order": {
            "side": side, "pair": pair, "order_type": "market_order",
            "total_quantity": quantity, "leverage": leverage,
            "margin_currency_short_name": "INR", "notification": "email_notification"
        }
    }
    json_body = json.dumps(body, separators=(',', ':'))
    signature = hmac.new(API_SECRET.encode('utf-8'), json_body.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': API_KEY, 'X-AUTH-SIGNATURE': signature}
    try:
        response = requests.post(url, data=json_body, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def monitor_coin(coin_name):
    pair = f"B-{coin_name}_USDT"
    in_position = False
    last_processed_time = None 
    entry_price = 0.0
    
    while True:
        try:
            config = CUSTOM_SETTINGS[coin_name]
            candles = get_futures_candles(pair, config["timeframe"])
            
            if candles:
                st_val, current_st, is_green_prev, is_red_to_green_flip, current_close, prev_close, candle_time = calculate_supertrend(candles)
                live_price = get_live_futures_price(pair)
                if live_price == 0:
                    live_price = current_close

                if st_val is not None and current_st is not None and candle_time is not None:
                    STATS[coin_name]["status"] = "IN_TRADE" if in_position else "MONITORING"
                    
                    print(f"⚡ [{coin_name}] Live: {live_price} | ST: {current_st:.4f} | Pos: {STATS[coin_name]['status']}", flush=True)
                    
                    # ENTRY: Sirf tabhi buy hoga jab Red to Green flip exact naye candle par detect ho
                    if not in_position:
                        if candle_time != last_processed_time:
                            if is_red_to_green_flip:
                                print(f"🟢 [{coin_name}] Red to Green Flip! Placing BUY order...", flush=True)
                                if place_order(pair, "buy", config["quantity"], config["leverage"]):
                                    in_position = True
                                    entry_price = live_price
                                    STATS[coin_name]["total_trades"] += 1
                                    STATS[coin_name]["status"] = "IN_TRADE"
                            last_processed_time = candle_time
                    
                    # EXIT: Live price Supertrend ke niche cross kare
                    elif in_position:
                        if live_price < current_st:
                            print(f"🔴 [{coin_name}] Price crossed below ST! Placing SELL order...", flush=True)
                            if place_order(pair, "sell", config["quantity"], config["leverage"]):
                                in_position = False
                                pnl_delta = live_price - entry_price
                                STATS[coin_name]["pnl"] += pnl_delta
                                if pnl_delta >= 0:
                                    STATS[coin_name]["wins"] += 1
                                else:
                                    STATS[coin_name]["losses"] += 1
                                STATS[coin_name]["status"] = "MONITORING"
        except Exception as e:
            print(f"❌ [{coin_name}] Error: {e}", flush=True)
        time.sleep(3)

def self_ping():
    while True:
        try:
            requests.get("http://127.0.0.1:10000/", timeout=5)
        except Exception:
            pass
        time.sleep(120)

def start_bot():
    time.sleep(2)
    for coin in CUSTOM_SETTINGS.keys():
        t = threading.Thread(target=monitor_coin, args=(coin,))
        t.daemon = True
        t.start()
    
    threading.Thread(target=self_ping, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
