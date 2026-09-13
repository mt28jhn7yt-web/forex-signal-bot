import os
import requests
from flask import Flask, render_template_string

app = Flask(__name__)

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Forex Signal Bot</title>
<style>
body{margin:0;background:#0f172a;color:white;font-family:Arial;padding:20px}
.card{max-width:520px;margin:auto;background:#1e293b;padding:25px;border-radius:22px}
h1{text-align:center;font-size:30px}
h2{text-align:center}
.signal{text-align:center;font-size:42px;font-weight:bold;margin:25px}
.buy{color:#22c55e}.sell{color:#ef4444}.wait{color:#facc15}
.row{display:flex;justify-content:space-between;padding:13px 0;border-bottom:1px solid #334155}
.small{text-align:center;color:#94a3b8;margin-top:20px}
</style>
</head>
<body>
<div class="card">
<h1>FOREX SIGNAL BOT</h1>
<h2>{{symbol}}</h2>

<div class="signal {{signal_class}}">{{signal}}</div>

<div class="row"><span>Price</span><span>{{price}}</span></div>
<div class="row"><span>Trend</span><span>{{trend}}</span></div>
<div class="row"><span>EMA 20</span><span>{{ema20}}</span></div>
<div class="row"><span>EMA 50</span><span>{{ema50}}</span></div>
<div class="row"><span>RSI</span><span>{{rsi}}</span></div>
<div class="row"><span>Confidence</span><span>{{confidence}}%</span></div>

{% if signal != "WAIT" %}
<div class="row"><span>Entry</span><span>{{entry}}</span></div>
<div class="row"><span>Stop Loss</span><span>{{stop}}</span></div>
<div class="row"><span>Take Profit 1</span><span>{{tp1}}</span></div>
<div class="row"><span>Take Profit 2</span><span>{{tp2}}</span></div>
{% endif %}

<div class="small">Live data • Refreshes every 60 seconds</div>
</div>
</body>
</html>
"""

def get_data():
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "EUR/USD",
            "interval": "15min",
            "outputsize": 100,
            "apikey": API_KEY
        },
        timeout=15
    )

    data = response.json()

    if "values" not in data:
        raise Exception(data.get("message", "Market data unavailable"))

    candles = list(reversed(data["values"]))
    closes = [float(c["close"]) for c in candles]

    price = closes[-1]

    ema20 = sum(closes[-20:]) / 20
    ema50 = sum(closes[-50:]) / 50

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    buy = 0
    sell = 0

    if price > ema20:
        buy += 30
    else:
        sell += 30

    if ema20 > ema50:
        buy += 30
    else:
        sell += 30

    if rsi > 55:
        buy += 25
    elif rsi < 45:
        sell += 25

    if buy >= 60:
        signal = "BUY"
        confidence = buy
        signal_class = "buy"
        trend = "Bullish"
    elif sell >= 60:
        signal = "SELL"
        confidence = sell
        signal_class = "sell"
        trend = "Bearish"
    else:
        signal = "WAIT"
        confidence = max(buy, sell)
        signal_class = "wait"
        trend = "Sideways"

    entry = price

    if signal == "BUY":
        stop = price - 0.0020
        tp1 = price + 0.0025
        tp2 = price + 0.0050
    elif signal == "SELL":
        stop = price + 0.0020
        tp1 = price - 0.0025
        tp2 = price - 0.0050
    else:
        stop = tp1 = tp2 = price

    return {
        "symbol": "EUR/USD",
        "signal": signal,
        "signal_class": signal_class,
        "confidence": confidence,
        "price": f"{price:.5f}",
        "trend": trend,
        "ema20": f"{ema20:.5f}",
        "ema50": f"{ema50:.5f}",
        "rsi": f"{rsi:.2f}",
        "entry": f"{entry:.5f}",
        "stop": f"{stop:.5f}",
        "tp1": f"{tp1:.5f}",
        "tp2": f"{tp2:.5f}"
    }

@app.route("/")
def home():
    try:
        return render_template_string(HTML, **get_data())
    except Exception as e:
        return f"<h2>Bot error: {e}</h2>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
