import os
import base64
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from openai import OpenAI

app = Flask(__name__)

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "XAU/USD"
]

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Forex Signal Bot</title>

<style>
body{
    margin:0;
    background:#0f172a;
    color:white;
    font-family:Arial;
    padding:20px;
}

.card{
    max-width:520px;
    margin:auto;
    background:#1e293b;
    padding:25px;
    border-radius:22px;
}

h1{
    text-align:center;
    font-size:30px;
}

h2{
    text-align:center;
}

select,button,input{
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin:8px 0;
    border:0;
    border-radius:12px;
    font-size:16px;
}

button{
    background:#334155;
    color:white;
    font-weight:bold;
}

.upload{
    margin-top:25px;
    padding-top:20px;
    border-top:1px solid #334155;
}

.signal{
    text-align:center;
    font-size:42px;
    font-weight:bold;
    margin:25px;
}

.buy{color:#22c55e}
.sell{color:#ef4444}
.wait{color:#facc15}

.row{
    display:flex;
    justify-content:space-between;
    padding:13px 0;
    border-bottom:1px solid #334155;
}

.small{
    text-align:center;
    color:#94a3b8;
    margin-top:20px;
}

.analysis{
    margin-top:20px;
    padding:15px;
    background:#0f172a;
    border-radius:15px;
    white-space:pre-wrap;
}
</style>
</head>

<body>

<div class="card">

<h1>FOREX SIGNAL BOT</h1>

<form method="get" action="/">
<select name="pair" onchange="this.form.submit()">

{% for p in pairs %}
<option value="{{p}}" {% if p == selected_pair %}selected{% endif %}>
{{p}}
</option>
{% endfor %}

</select>
</form>

<form method="get" action="/">
<input type="hidden" name="pair" value="{{selected_pair}}">
<button type="submit">🔄 REFRESH MARKET DATA</button>
</form>

<h2>{{symbol}}</h2>

<div class="signal {{signal_class}}">
{{signal}}
</div>

<div class="row">
<span>Price</span>
<span>{{price}}</span>
</div>

<div class="row">
<span>Trend</span>
<span>{{trend}}</span>
</div>

<div class="row">
<span>EMA 20</span>
<span>{{ema20}}</span>
</div>

<div class="row">
<span>EMA 50</span>
<span>{{ema50}}</span>
</div>

<div class="row">
<span>RSI</span>
<span>{{rsi}}</span>
</div>

<div class="row">
<span>Confidence</span>
<span>{{confidence}}%</span>
</div>

{% if signal != "WAIT" %}

<div class="row">
<span>Entry</span>
<span>{{entry}}</span>
</div>

<div class="row">
<span>Stop Loss</span>
<span>{{stop}}</span>
</div>

<div class="row">
<span>Take Profit 1</span>
<span>{{tp1}}</span>
</div>

<div class="row">
<span>Take Profit 2</span>
<span>{{tp2}}</span>
</div>

{% endif %}

<div class="upload">

<h3>📷 Analyze MT5 Screenshot</h3>

<form method="post"
      action="/analyze"
      enctype="multipart/form-data">

<input type="hidden"
       name="pair"
       value="{{selected_pair}}">

<input type="file"
       name="chart"
       accept="image/*"
       required>

<button type="submit">
🤖 ANALYZE CURRENT TRADE
</button>

</form>

{% if analysis %}

<div class="analysis">
<strong>AI CHART ANALYSIS</strong>

{{analysis}}
</div>

{% endif %}

</div>

<div class="small">
Live data • Automatic refresh every 5 minutes
</div>

</div>

</body>
</html>
"""


def get_data(pair):

    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": pair,
            "interval": "15min",
            "outputsize": 100,
            "apikey": TWELVE_KEY
        },
        timeout=15
    )

    data = response.json()

    if "values" not in data:
        raise Exception(
            data.get(
                "message",
                "Market data unavailable"
            )
        )

    candles = list(reversed(data["values"]))

    closes = [
        float(c["close"])
        for c in candles
    ]

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

        rsi = 100 - (
            100 / (1 + rs)
        )

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
        confidence = max(
            buy,
            sell
        )

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

        stop = price
        tp1 = price
        tp2 = price

    return {
        "symbol": pair,
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

    pair = request.args.get(
        "pair",
        "EUR/USD"
    )

    if pair not in PAIRS:
        pair = "EUR/USD"

    try:

        result = get_data(pair)

        return render_template_string(
            HTML,
            **result,
            pairs=PAIRS,
            selected_pair=pair,
            analysis=None
        )

    except Exception as e:

        return f"<h2>Bot error: {e}</h2>"


@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    pair = request.form.get(
        "pair",
        "EUR/USD"
    )

    chart = request.files.get(
        "chart"
    )

    if not chart:
        return redirect(
            url_for(
                "home",
                pair=pair
            )
        )

    if not OPENAI_KEY:

        return "<h2>OPENAI_API_KEY is not configured.</h2>"

    try:

        market = get_data(pair)

        image_bytes = chart.read()

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        client = OpenAI(
            api_key=OPENAI_KEY
        )

        prompt = f"""
You are a professional technical-analysis assistant.

Analyze this MT5 trading chart screenshot.

Current pair:
{pair}

Current live market price:
{market["price"]}

Current calculated trend:
{market["trend"]}

RSI:
{market["rsi"]}

EMA 20:
{market["ema20"]}

EMA 50:
{market["ema50"]}

Give a concise analysis.

Check:
1. Market structure
2. Trend
3. Support and resistance
4. Candlestick momentum
5. Possible BUY or SELL setup
6. Whether to WAIT
7. Suggested entry area
8. Stop-loss area
9. Take-profit areas
10. Main reason for the decision

Final recommendation must be exactly one of:

BUY
SELL
WAIT

Do not claim certainty. This is analysis, not guaranteed financial advice.
"""

        response = client.responses.create(

            model="gpt-5.6-luna",

            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url":
                            f"data:image/jpeg;base64,{encoded}"
                        }
                    ]
                }
            ]
        )

        analysis = response.output_text

        return render_template_string(
            HTML,
            **market,
            pairs=PAIRS,
            selected_pair=pair,
            analysis=analysis
        )

    except Exception as e:

        return f"<h2>AI analysis error: {e}</h2>"


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
