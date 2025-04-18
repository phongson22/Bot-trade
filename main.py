import os
import time
import threading
import requests
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from ta.trend import EMAIndicator
from telegram.ext import Updater, CommandHandler

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_SECRET_KEY")
client = Client(api_key, api_secret)

telegram_token = "7037849782:AAHayUH80ln_QPJDoUmI1re6daTevCr4P04"
telegram_chat_id = "513567776"

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
intervals = {
    "M15": Client.KLINE_INTERVAL_15MINUTE,
    "M30": Client.KLINE_INTERVAL_30MINUTE,
    "H1": Client.KLINE_INTERVAL_1HOUR,
    "H4": Client.KLINE_INTERVAL_4HOUR,
    "D1": Client.KLINE_INTERVAL_1DAY,
    "W": Client.KLINE_INTERVAL_1WEEK,
    "M": Client.KLINE_INTERVAL_1MONTH,
}
CHECK_INTERVAL_MINUTES = 1

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": telegram_chat_id, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        print("Không gửi được Telegram")

def get_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
    df = pd.DataFrame(klines, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        '_', '_', '_', '_', '_', '_'
    ])
    df['close'] = df['close'].astype(float)
    return df

def check_ema_crossover(df):
    ema34 = EMAIndicator(close=df['close'], window=34).ema_indicator()
    ema89 = EMAIndicator(close=df['close'], window=89).ema_indicator()
    if ema34.iloc[-2] < ema89.iloc[-2] and ema34.iloc[-1] > ema89.iloc[-1]:
        return "BUY"
    elif ema34.iloc[-2] > ema89.iloc[-2] and ema34.iloc[-1] < ema89.iloc[-1]:
        return "SELL"
    else:
        return None

def check_all_pairs():
    for symbol in symbols:
        for name, interval in intervals.items():
            try:
                df = get_data(symbol, interval)
                signal = check_ema_crossover(df)
                if signal:
                    msg = f"DEMO: {signal} tại {symbol} - khung {name}"
                    print(msg)
                    send_telegram(msg)
                else:
                    print(f"{symbol} [{name}]: Không có tín hiệu.")
            except Exception as e:
                print(f"Lỗi {symbol} [{name}]: {e}")

def run_bot():
    while True:
        check_all_pairs()
        print(f"--- Đợi {CHECK_INTERVAL_MINUTES} phút để kiểm tra lại ---\n")
        time.sleep(60 * CHECK_INTERVAL_MINUTES)

def status(update, context):
    msg = f"Bot đang chạy.\nCặp: {symbols}\nKhung: {', '.join(intervals.keys())}"
    context.bot.send_message(chat_id=telegram_chat_id, text=msg)

def run_telegram():
    updater = Updater(token=telegram_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("status", status))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    send_telegram("✅ Tín hiệu TEST: Hệ thống Telegram hoạt động chính xác!")
    threading.Thread(target=run_bot).start()
    threading.Thread(target=run_telegram).start()
