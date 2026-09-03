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

TRADE_SIZE = 700          
TRADE_LEVERAGE = 10       
TRADE_SIDE = "buy"        
# =====================================================================

BASE_URL = "https://api.coindcx.com"

def get_all_active_instruments():
    try:
        url = BASE_URL + "/exchange/v1/derivatives/futures/data/active_instruments"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            instruments = response.json()
            print("📋 All Active Futures Instruments:", flush=True)
            for inst in instruments:
                if "XAU" in str(inst).upper():
                    print(f"   -> Found Match: {inst}", flush=True)
    except Exception as e:
        print(f"❌ Error fetching instruments: {e}", flush=True)

def bot_loop():
    time.sleep(3)
    get_all_active_instruments()
    while True:
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
