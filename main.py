import os
import time
import threading
import requests
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from ta.trend import EMAIndicator
from telegram.ext import Updater, CommandHandler
import mplfinance as mpf

# Load biến môi trường từ file .env
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_SECRET_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

client = Client(api_key, api_secret)

# Cấu hình bot
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
intervals = {
    "M15": Client.KLINE_INTERVAL_15MINUTE,
    "M30": Client.KLINE_INTERVAL_30MINUTE,
    "H1": Client.KLINE_INTERVAL_1HOUR,
    "H4": Client.KLINE_INTERVAL_4HOUR,
    "D1": Client.KLINE_INTERVAL_1DAY
}
CHECK_INTERVAL_MINUTES = 1
last_signals = {}

# Gửi tin nhắn Telegram (kèm ảnh nếu có)
def send_telegram(msg, image_path=None):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": telegram_chat_id, "text": msg}
    try:
        requests.post(url, data=data)
        if image_path:
            send_chart(image_path)
    except Exception as e:
        print(f"Lỗi gửi telegram: {e}")

# Gửi ảnh biểu đồ
def send_chart(image_path):
    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    with open(image_path, 'rb') as photo:
        data = {"chat_id": telegram_chat_id}
        files = {"photo": photo}
        requests.post(url, data=data, files=files)

# Lấy dữ liệu từ Binance
def get_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
    df = pd.DataFrame(klines, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        '_', '_', '_', '_', '_', '_'
    ])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.set_index('time', inplace=True)
    df = df.astype(float)
    return df

# Kiểm tra tín hiệu EMA giao cắt
def check_ema_crossover(df):
    df['EMA34'] = EMAIndicator(close=df['close'], window=34).ema_indicator()
    df['EMA89'] = EMAIndicator(close=df['close'], window=89).ema_indicator()
    if df['EMA34'].iloc[-2] < df['EMA89'].iloc[-2] and df['EMA34'].iloc[-1] > df['EMA89'].iloc[-1]:
        return "BUY", df['close'].iloc[-1]
    elif df['EMA34'].iloc[-2] > df['EMA89'].iloc[-2] and df['EMA34'].iloc[-1] < df['EMA89'].iloc[-1]:
        return "SELL", df['close'].iloc[-1]
    return None, None

# Vẽ biểu đồ nến Nhật
def plot_chart(df, symbol, interval, signal, entry_price):
    save_path = f"{symbol}_{interval}_signal.png"
    apds = [
        mpf.make_addplot(df['EMA34'], color='blue'),
        mpf.make_addplot(df['EMA89'], color='red')
    ]
    title = f"{symbol} - {interval} | {signal} @ {entry_price:.2f}"
    mpf.plot(df, type='candle', style='yahoo', addplot=apds,
             title=title, ylabel='Price', savefig=save_path)
    return save_path

# Quét toàn bộ cặp + khung thời gian
def check_all_pairs():
    for symbol in symbols:
        for name, interval in intervals.items():
            try:
                df = get_data(symbol, interval)
                signal, entry = check_ema_crossover(df)
                key = (symbol, name)
                if signal and last_signals.get(key) != signal:
                    image_path = plot_chart(df, symbol, name, signal, entry)
                    msg = f"DEMO: {signal} tại {symbol} [{name}] | Entry: {entry:.2f}"
                    send_telegram(msg, image_path)
                    last_signals[key] = signal
                else:
                    print(f"{symbol} [{name}]: Không có tín hiệu mới.")
            except Exception as e:
                print(f"Lỗi {symbol} [{name}]: {e}")

# Luồng chạy bot
def run_bot():
    while True:
        check_all_pairs()
        print(f"--- Đợi {CHECK_INTERVAL_MINUTES} phút để kiểm tra lại ---\n")
        time.sleep(60 * CHECK_INTERVAL_MINUTES)

# Lệnh Telegram
def status(update, context):
    msg = f"Bot đang chạy.\nCặp: {symbols}\nKhung: {', '.join(intervals.keys())}"
    context.bot.send_message(chat_id=telegram_chat_id, text=msg)

# Luồng Telegram
def run_telegram():
    updater = Updater(token=telegram_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("status", status))
    updater.start_polling()
    updater.idle()

# Khởi chạy
if __name__ == "__main__":
    send_telegram("✅ Tín hiệu TEST: Bot đã hoạt động và sẵn sàng chiến đấu!")
    threading.Thread(target=run_bot).start()
    run_telegram()
