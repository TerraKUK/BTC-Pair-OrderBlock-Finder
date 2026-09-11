import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_BASE_URL = "https://api.binance.us"
DATA_DIR = "data"
RAW_DATA_DIR = f"{DATA_DIR}/raw"

# Stablecoins to exclude from scanning
STABLECOINS = {
    "USDC", "USDT", "BUSD", "DAI", "TUSD", "USDP", "USDD",
    "USD1", "FDUSD", "PYUSD", "USDE", "USDS", "USDF", "GUSD",
    "UST", "USTC", "FRAX", "LUSD", "SUSD", "MIM", "ALUSD"
}

API_KEY = os.getenv("BINANCE_API_KEY")

os.makedirs(RAW_DATA_DIR, exist_ok=True)


def fetch_all_pairs():
    endpoint = f"{API_BASE_URL}/api/v3/exchangeInfo"
    response = requests.get(endpoint)
    response.raise_for_status()
    data = response.json()
    return [
        symbol['symbol']
        for symbol in data['symbols']
        if symbol['quoteAsset'] == "USDT"
        and symbol['status'] == "TRADING"
        and symbol['baseAsset'] not in STABLECOINS
    ]


def fetch_and_save_raw_data(pair):
    endpoint = f"{API_BASE_URL}/api/v3/klines"
    start_date = datetime.now(timezone.utc) - timedelta(days=730)
    params = {
        "symbol": pair,
        "interval": "4h",
        "startTime": int(start_date.timestamp() * 1000),
        "limit": 1000
    }
    headers = {"X-MBX-APIKEY": API_KEY} if API_KEY else {}

    all_data = []
    while True:
        response = requests.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        batch_data = response.json()
        if not batch_data:
            break
        all_data.extend(batch_data)
        params["startTime"] = batch_data[-1][0] + 1

    df = pd.DataFrame(all_data, columns=[
        "ts", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "num_trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["ts"] = pd.to_datetime(df["ts"], unit='ms')
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

    output_file = f"{RAW_DATA_DIR}/{pair}_4h.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved raw data for {pair} to {output_file}")


def update_all_raw_data():
    pairs = fetch_all_pairs()
    print(f"Found {len(pairs)} pairs to fetch")
    for pair in pairs:
        try:
            fetch_and_save_raw_data(pair)
        except Exception as e:
            print(f"Failed to fetch {pair}: {e}")


if __name__ == "__main__":
    update_all_raw_data()
