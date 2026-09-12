import os
import pandas as pd

RAW_DATA_DIR = "data/raw"
ORDER_BLOCK_DIR = "data/orderblocks"

os.makedirs(ORDER_BLOCK_DIR, exist_ok=True)

def detect_order_blocks(df, pair):
    order_blocks = []
    for i in range(1, len(df)):
        prev_candle = df.iloc[i - 1]
        curr_candle = df.iloc[i]

        if (
            prev_candle["close"] == prev_candle["low"]
            and curr_candle["open"] == prev_candle["close"]
            and curr_candle["low"] == prev_candle["close"]
            and (curr_candle["close"] - curr_candle["open"]) > (prev_candle["open"] - prev_candle["close"])
        ):
            order_blocks.append({"date_time": prev_candle["ts"], "price": prev_candle["open"], "type": "bullish"})

        elif (
            prev_candle["close"] == prev_candle["high"]
            and curr_candle["open"] == prev_candle["close"]
            and curr_candle["high"] == prev_candle["close"]
            and (curr_candle["open"] - curr_candle["close"]) > (prev_candle["close"] - prev_candle["open"])
        ):
            order_blocks.append({"date_time": prev_candle["ts"], "price": prev_candle["open"], "type": "bearish"})

    return order_blocks

def update_order_block_data():
    raw_files = os.listdir(RAW_DATA_DIR)
    for file_name in raw_files:
        asset = file_name.split("_")[0]
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        df = pd.read_csv(file_path, parse_dates=["ts"])
        
        order_blocks = detect_order_blocks(df, asset)
        
        if order_blocks:
            output_df = pd.DataFrame(order_blocks)
            output_df.to_csv(f"{ORDER_BLOCK_DIR}/{asset}_orderblocks.csv", index=False)
            print(f"Order blocks saved for {asset}")

if __name__ == "__main__":
    update_order_block_data()
