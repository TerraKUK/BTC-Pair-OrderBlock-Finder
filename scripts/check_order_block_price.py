import os
import glob
import requests
import pandas as pd

API_BASE_URL = "https://api.binance.us"
ORDER_BLOCK_DIR = "data/orderblocks"
SENT_ALERTS_FILE = "data/sent_alerts.txt"
THRESHOLD = 0.02

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_alert(message):
    send_std_alert(message)
    send_telegram_alert(message)


def send_std_alert(message):
    print(message)


def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    response.raise_for_status()


def load_sent_alerts():
    """Загружает уже отправленные сигналы из файла."""
    if os.path.exists(SENT_ALERTS_FILE):
        with open(SENT_ALERTS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()


def save_sent_alerts(sent_alerts):
    """Сохраняет отправленные сигналы в файл."""
    os.makedirs(os.path.dirname(SENT_ALERTS_FILE), exist_ok=True)
    with open(SENT_ALERTS_FILE, "w") as f:
        f.write("\n".join(sent_alerts))


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
    new_alerts = []
    triggered_alerts = []

    for file_path in csv_files:
        asset = os.path.basename(file_path).split("_")[0]
        df = pd.read_csv(file_path, parse_dates=["date_time"])

        try:
            current_price = fetch_current_price(asset)
            for _, row in df.iterrows():
                order_block_price = row["price"]
                order_block_type = row["type"]

                is_bullish_signal = (
                    order_block_type == "bullish"
                    and order_block_price <= current_price <= order_block_price * (1 + THRESHOLD)
                )
                is_bearish_signal = (
                    order_block_type == "bearish"
                    and order_block_price * (1 - THRESHOLD) <= current_price <= order_block_price
                )

                if is_bullish_signal or is_bearish_signal:
                    alert_key = f"{asset}_{order_block_type}_{order_block_price}"

                    if alert_key in sent_alerts:
                        continue

                    message = (
                        f"{asset} has reached {order_block_type} order block "
                        f"price at {order_block_price}. Current price: {current_price}"
                    )
                    send_alert(message)
                    triggered_alerts.append(message)
                    new_alerts.append(alert_key)
                    sent_alerts.add(alert_key)

        except Exception as e:
            print(f"Failed to check price for {asset}: {e}")

    if new_alerts:
        save_sent_alerts(sent_alerts)

    if not triggered_alerts:
        print("No order block prices reached in this check.")


if __name__ == "__main__":
    check_order_block_prices()
