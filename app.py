import os
import requests
from flask import Flask, render_template_string

app = Flask(__name__)

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Forex Signal Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: white;
            padding: 20px;
        }
        .card {
            max-width: 500px;
            margin: auto;
            background: #1e293b;
            padding: 25px;
            border-radius: 20px;
        }
        h1 { text-align: center; }
        .signal {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
        }
        .buy { color: #22c55e; }
        .sell { color: #ef4444; }
        .wait { color: #facc15; }
        .row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #334155;
        }
    </style>
</head>
<body>
<div class="card">
    <h1>FOREX SIGNAL BOT</h1>

    {% if error %}
        <p>{{ error }}</p>
    {% else %}
        <h2>{{ symbol }}</h2>

        <div class="signal {{ signal_class }}">
            {{ signal }}
        </div>

        <div class="row">
            <span>Price</span>
            <span>{{ price }}</span>
        </div>

        <div class="row">
            <span>EMA 20</span>
            <span>{{ ema20 }}</span>
        </div>

        <div class="row">
            <span>EMA 50</span>
            <span>{{ ema50 }}</span>
        </div>

        <div class="row">
            <span>RSI</span>
            <span>{{ rsi }}</span>
        </div>

        <div class="row">
            <span>Confidence</span>
            <span>{{ confidence }}%</span>
        </div>

        <p style="text-align:center">
            Updates every 60 seconds
        </p>
    {% endif %}
</div>
</body>
</html>
"""

def get_data():
    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "EUR/USD",
        "interval": "15min",
        "outputsize": 100,
        "apikey": API_KEY
    }

    response = requests.get(url, params=params, timeout=15)
    data = response.json()

    if "values" not in data:
        raise Exception(data.get("message", "Unable to get market data"))

    candles = list(reversed(data["values"]))

    closes = [float(x["close"]) for x in candles]

    price = closes[-1]

    ema20 = sum(closes[-20:]) / 20
    ema50 = sum(closes[-50:]) / 50

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    buy_score = 0
    sell_score = 0

    if price > ema20:
        buy_score += 30
    else:
        sell_score += 30

    if ema20 > ema50:
        buy_score += 30
    else:
        sell_score += 30

    if rsi > 50:
        buy_score += 20
    else:
        sell_score += 20

    if buy_score >= 60:
        signal = "BUY"
        confidence = buy_score
        signal_class = "buy"
    elif sell_score >= 60:
        signal = "SELL"
        confidence = sell_score
        signal_class = "sell"
    else:
        signal = "WAIT"
        confidence = max(buy_score, sell_score)
        signal_class = "wait"

    return {
        "symbol": "EUR/USD",
        "signal": signal,
        "signal_class": signal_class,
        "confidence": confidence,
        "price": round(price, 5),
        "ema20": round(ema20, 5),
        "ema50": round(ema50, 5),
        "rsi": round(rsi, 2)
    }


@app.route("/")
def home():
    try:
        result = get_data()
        return render_template_string(HTML, **result, error=None)
    except Exception as e:
        return render_template_string(
            HTML,
            error=str(e),
            symbol="",
            signal="",
            signal_class="",
            confidence="",
            price="",
            ema20="",
            ema50="",
            rsi=""
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
