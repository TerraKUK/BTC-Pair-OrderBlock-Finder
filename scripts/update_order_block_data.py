import os
import pandas as pd

RAW_DATA_DIR = "data/raw"
ORDER_BLOCK_DIR = "data/orderblocks"

# Minimum candle range as % of price (skip doji/narrow candles)
MIN_CANDLE_RANGE_PCT = 0.005  # 0.5%

# Minimum impulse strength (curr move must be > prev move * this multiplier)
MIN_IMPULSE_MULTIPLIER = 1.2

os.makedirs(ORDER_BLOCK_DIR, exist_ok=True)


def is_valid_candle(candle):
    """Check if candle is wide enough (not a doji)."""
    candle_range = candle["high"] - candle["low"]
    if candle["close"] <= 0:
        return False
    return (candle_range / candle["close"]) >= MIN_CANDLE_RANGE_PCT


def detect_order_blocks(df, pair):
    order_blocks = []
    for i in range(1, len(df)):
        prev_candle = df.iloc[i - 1]
        curr_candle = df.iloc[i]

        # Skip narrow/doji candles
        if not is_valid_candle(prev_candle):
            continue

        prev_body = abs(prev_candle["open"] - prev_candle["close"])
        curr_body = abs(curr_candle["close"] - curr_candle["open"])

        # Bullish OB: prev closed at low, curr opened at same level, curr impulse stronger
        if (
            prev_candle["close"] <= prev_candle["low"] * 1.001
            and curr_candle["open"] <= prev_candle["close"] * 1.001
            and curr_candle["low"] <= prev_candle["close"] * 1.001
            and curr_body >= prev_body * MIN_IMPULSE_MULTIPLIER
        ):
            order_blocks.append({
                "date_time": prev_candle["ts"],
                "price": prev_candle["open"],
                "type": "bullish"
            })

        # Bearish OB: prev closed at high, curr opened at same level, curr impulse stronger
        elif (
            prev_candle["close"] >= prev_candle["high"] * 0.999
            and curr_candle["open"] >= prev_candle["close"] * 0.999
            and curr_candle["high"] >= prev_candle["close"] * 0.999
            and curr_body >= prev_body * MIN_IMPULSE_MULTIPLIER
        ):
            order_blocks.append({
                "date_time": prev_candle["ts"],
                "price": prev_candle["open"],
                "type": "bearish"
            })

    return order_blocks


def update_order_block_data():
    raw_files = os.listdir(RAW_DATA_DIR)
    for file_name in raw_files:
        if not file_name.endswith(".csv"):
            continue
        asset = file_name.split("_")[0]
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        df = pd.read_csv(file_path, parse_dates=["ts"])

        order_blocks = detect_order_blocks(df, asset)

        if order_blocks:
            output_df = pd.DataFrame(order_blocks)
            output_df.to_csv(f"{ORDER_BLOCK_DIR}/{asset}_orderblocks.csv", index=False)
            print(f"Order blocks saved for {asset} ({len(order_blocks)} zones)")


if __name__ == "__main__":
    update_order_block_data()
