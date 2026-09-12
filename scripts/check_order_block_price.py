import os
import json
import glob
import requests
import pandas as pd

API_BASE_URL = "https://api.binance.us"
ORDER_BLOCK_DIR = "data/orderblocks"
SENT_ALERTS_FILE = "data/sent_alerts.txt"
LAST_PRICES_FILE = "data/last_prices.json"

ZONE_WIDTH = 0.02  # 2% zone width

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_alert(message):
    print(message)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    response.raise_for_status()


def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()


def save_sent_alerts(sent_alerts):
    os.makedirs(os.path.dirname(SENT_ALERTS_FILE), exist_ok=True)
    with open(SENT_ALERTS_FILE, "w") as f:
        f.write("\n".join(sent_alerts))


def load_last_prices():
    if os.path.exists(LAST_PRICES_FILE):
        with open(LAST_PRICES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_last_prices(prices):
    os.makedirs(os.path.dirname(LAST_PRICES_FILE), exist_ok=True)
    with open(LAST_PRICES_FILE, "w") as f:
        json.dump(prices, f, indent=2)


def fetch_current_price(symbol):
    endpoint = f"{API_BASE_URL}/api/v3/ticker/price"
    params = {"symbol": symbol}
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    data = response.json()
    return float(data["price"])


def check_order_block_prices():
    csv_files = glob.glob(os.path.join(ORDER_BLOCK_DIR, "*.csv"))
    sent_alerts = load_sent_alerts()
    last_prices = load_last_prices()
    new_sent = set()
    new_prices = {}
    triggered = 0

    for file_path in csv_files:
        asset = os.path.basename(file_path).split("_")[0]
        df = pd.read_csv(file_path, parse_dates=["date_time"])

        try:
            current_price = fetch_current_price(asset)
            last_price = last_prices.get(asset)
            new_prices[asset] = current_price

            for _, row in df.iterrows():
                ob_price = row["price"]
                ob_type = row["type"]

                if ob_type == "bullish":
                    zone_top = ob_price
                    zone_bottom = ob_price * (1 - ZONE_WIDTH)
                    entered = (last_price is not None and last_price > zone_bottom and current_price <= zone_bottom)
                elif ob_type == "bearish":
                    zone_top = ob_price * (1 + ZONE_WIDTH)
                    zone_bottom = ob_price
                    entered = (last_price is not None and last_price < zone_top and current_price >= zone_top)
                else:
                    continue

                # Signal 1: entered zone (one-time)
                enter_key = f"{asset}_{ob_type}_{ob_price}_entered"
                if entered and enter_key not in sent_alerts:
                    emoji = "\U0001F7E2"  # green
                    msg = f"{emoji} {asset} entered {ob_type} OB ({ob_price}). Now: {current_price}"
                    send_alert(msg)
                    new_sent.add(enter_key)
                    sent_alerts.add(enter_key)
                    triggered += 1

                # Signal 2: in zone (reset on exit)
                in_zone_key = f"{asset}_{ob_type}_{ob_price}_in_zone"
                if zone_bottom <= current_price <= zone_top:
                    if in_zone_key not in sent_alerts:
                        emoji = "\U0001F7E1"  # yellow
                        msg = f"{emoji} {asset} in {ob_type} OB zone ({ob_price}). Now: {current_price}"
                        send_alert(msg)
                        new_sent.add(in_zone_key)
                        sent_alerts.add(in_zone_key)
                        triggered += 1
                else:
                    # Price exited zone — remove in_zone key so it can trigger again
                    if in_zone_key in sent_alerts:
                        sent_alerts.discard(in_zone_key)

        except Exception as e:
            print(f"Failed to check price for {asset}: {e}")

    if new_sent:
        save_sent_alerts(sent_alerts)

    save_last_prices(new_prices)

    if triggered == 0:
        print("No order block signals in this check.")


if __name__ == "__main__":
    check_order_block_prices()
