from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from mysql.connector import pooling
import os, uuid
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
import talib

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, Dense

# ---------------------------
# Flask App
# ---------------------------
app = Flask(__name__)
CORS(app)

GRAPH_DIR = "graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# ---------------------------
# MySQL Connection Pool
# ---------------------------
dbconfig = {
    "host": "b1tt9nyayx7p9phrpayp-mysql.services.clever-cloud.com",
    "user": "uqbh2a5hvufqxpzz",
    "password": "apfDd7dOBHhZdKJXXyFc",
    "database": "b1tt9nyayx7p9phrpayp",
    "port": 3306
}

cnxpool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=3,   # clever cloud limit safe
    **dbconfig
)

def get_db_connection():
    return cnxpool.get_connection()

# ---------------------------
# DB SAVE FUNCTION (SAFE)
# ---------------------------
def save_prices_to_db(df, symbol):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS btc_prices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20),
            time DATETIME,
            open FLOAT,
            high FLOAT,
            low FLOAT,
            close FLOAT,
            volume FLOAT,
            UNIQUE(symbol, time)
        )
        """)

        query = """
        INSERT IGNORE INTO btc_prices
        (symbol, time, open, high, low, close, volume)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        values = [
            (
                symbol,
                row.time,
                row.open,
                row.high,
                row.low,
                row.close,
                row.volume
            )
            for row in df.itertuples()
        ]

        cursor.executemany(query, values)
        conn.commit()

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ---------------------------
# AUTH
# ---------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username=%s", (data["username"],))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Kullanıcı var"}), 400

    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s,%s)",
        (data["username"], data["password"])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"msg": "Kayıt başarılı"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password FROM users WHERE username=%s",
        (data["username"],)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or row[0] != data["password"]:
        return jsonify({"error": "Hatalı giriş"}), 401

    return jsonify({"msg": "Giriş başarılı"})

# ---------------------------
# PREDICT
# ---------------------------
@app.route("/predict")
def predict():
    symbol = request.args.get("symbol")

    if not symbol:
        return jsonify({"error": "symbol gerekli"}), 400

    # ---------------------------
    # FETCH 1 YEAR DATA
    # ---------------------------
    url = f"https://api.kucoin.com/api/v1/market/candles?type=1day&symbol={symbol}"
    r = requests.get(url)
    if r.status_code != 200:
        return jsonify({"error": "KuCoin API hatası"}), 500

    df = pd.DataFrame(
        r.json()["data"],
        columns=["time","open","close","high","low","volume","turnover"]
    )

    df["time"] = pd.to_datetime(df["time"].astype(int), unit="s")
    df = df.astype({
        "open": float,
        "close": float,
        "high": float,
        "low": float,
        "volume": float
    })

    df = df.sort_values("time").reset_index(drop=True)
    df.drop(columns=["turnover"], inplace=True)

    # ---------------------------
    # INDICATORS
    # ---------------------------
    df["MA10"] = talib.SMA(df["close"], 10)
    df["MA20"] = talib.SMA(df["close"], 20)
    df["RSI"] = talib.RSI(df["close"], 14)
    df["MACD"], _, _ = talib.MACD(df["close"])

    df.fillna(0, inplace=True)

    # ---------------------------
    # FEATURES & SCALE
    # ---------------------------
    features = ["open","high","low","close","volume","MA10","MA20","RSI","MACD"]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[features])

    lookback = 60
    close_idx = features.index("close")

    X, y = [], []
    for i in range(lookback, len(scaled)):
        X.append(scaled[i-lookback:i])
        y.append(scaled[i, close_idx])

    X = np.array(X)
    y = np.array(y)

    if len(X) < 10:
        return jsonify({"error": "Yetersiz veri"}), 400

    # 🔒 GÜVENLİ TEST GÜN SAYISI
    test_days = min(100, len(X) - 1)

    # ---------------------------
    # MODEL (TÜM VERİYLE EĞİT)
    # ---------------------------
    model = Sequential([
        LSTM(50, input_shape=(X.shape[1], X.shape[2])),
        Dense(1)
    ])

    model.compile(optimizer="adam", loss="mse")
    model.fit(X, y, epochs=10, batch_size=8, verbose=0)

    # ---------------------------
    # 1️⃣ TEST (GERÇEKLE ÖRTÜŞEN)
    # ---------------------------
    fit_preds = model.predict(X[:test_days], verbose=0)

    temp = np.zeros((len(fit_preds), len(features)))
    temp[:, close_idx] = fit_preds.flatten()
    fit_close = scaler.inverse_transform(temp)[:, close_idx]

    # ---------------------------
    # 2️⃣ GELECEK TAHMİN (ROLLING)
    # ---------------------------
    rolling_input = X[test_days - 1].copy()
    future_preds = []

    steps = len(df) - (lookback + test_days)

    for _ in range(steps):
        p = model.predict(rolling_input[np.newaxis, :, :], verbose=0)[0, 0]
        future_preds.append(p)

        rolling_input = np.roll(rolling_input, -1, axis=0)
        rolling_input[-1, close_idx] = p

    temp2 = np.zeros((len(future_preds), len(features)))
    temp2[:, close_idx] = future_preds
    future_close = scaler.inverse_transform(temp2)[:, close_idx]

    # ---------------------------
    # TAHMİN ÇİZGİSİ (TEK PARÇA)
    # ---------------------------
    pred_line = np.full(len(df), np.nan)

    pred_line[lookback:lookback + test_days] = fit_close

    start = lookback + test_days
    pred_line[start:start + len(future_close)] = future_close

    # ---------------------------
    # GRAPH
    # ---------------------------
    img = f"{uuid.uuid4()}.png"
    path = os.path.join(GRAPH_DIR, img)

    plt.figure(figsize=(12, 6))
    plt.plot(df["time"], df["close"], label="Gerçek Fiyat", linewidth=2)
    plt.plot(df["time"], pred_line, label="Model Tahmini", linewidth=2)

    plt.title(f"{symbol} - Son 1 Yıl Fiyat & Tahmin")
    plt.xlabel("Tarih")
    plt.ylabel("USDT")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

    return jsonify({
        "symbol": symbol,
        "graph": f"http://localhost:5000/graph/{img}"
    })

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)