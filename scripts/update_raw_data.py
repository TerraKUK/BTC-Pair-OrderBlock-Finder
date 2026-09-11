RAW_DATA_DIR = f"{DATA_DIR}/raw"

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
        if symbol['quoteAsset'] == "USDT" and symbol['status'] == "TRADING"
    ]

def fetch_and_save_raw_data(pair):
    """Fetches 4-hour historical data for a given pair and saves to a CSV file."""
    endpoint = f"{API_BASE_URL}/api/v3/klines"
    start_date = datetime.now(timezone.utc) - timedelta(days=730)  # Use timezone-aware datetime
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
        params["startTime"] = batch_data[-1][0] + 1  # Continue from the last timestamp

    df = pd.DataFrame(all_data, columns=["ts", "open", "high", "low", "close", "volume", "close_time",
                                         "quote_asset_volume", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"])
    df["ts"] = pd.to_datetime(df["ts"], unit='ms')
    
    # Only convert numeric columns to float
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

    output_file = f"{RAW_DATA_DIR}/{pair}_4h.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved raw data for {pair} to {output_file}")

def update_all_raw_data():
    pairs = fetch_all_pairs()
    for pair in pairs:
        fetch_and_save_raw_data(pair)

if __name__ == "__main__":
    update_all_raw_data()
