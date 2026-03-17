#!/usr/bin/env python3
from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

def calculate_ema(closes, period):
    ema = []
    multiplier = 2 / (period + 1)
    for i in range(len(closes)):
        if i < period - 1:
            ema.append(None)
        elif i == period - 1:
            ema.append(round(sum(closes[:period]) / period, 4))
        else:
            ema.append(round((closes[i] - ema[-1]) * multiplier + ema[-1], 4))
    return ema

def calculate_rsi(closes, period=14):
    rsi = []
    for i in range(len(closes)):
        if i < period:
            rsi.append(None)
            continue
        gains, losses = [], []
        for j in range(i - period + 1, i + 1):
            diff = closes[j] - closes[j-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(round(100 - (100 / (1 + rs)), 2))
    return rsi

def calculate_bollinger_bands(closes, period=20, std_dev=2):
    upper, lower, middle = [], [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None); lower.append(None); middle.append(None)
        else:
            window = closes[i-period+1:i+1]
            ma = sum(window) / period
            std = (sum((x - ma) ** 2 for x in window) / period) ** 0.5
            upper.append(round(ma + std_dev * std, 4))
            lower.append(round(ma - std_dev * std, 4))
            middle.append(round(ma, 4))
    return upper, middle, lower

def find_swing_points(highs, lows, timestamps, window=4):
    swing_highs, swing_lows = [], []
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append({"index": i, "x": timestamps[i], "y": round(highs[i], 4)})
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append({"index": i, "x": timestamps[i], "y": round(lows[i], 4)})
    return swing_highs, swing_lows

def detect_patterns(swing_highs, swing_lows):
    patterns = []
    sh = swing_highs[-6:] if len(swing_highs) >= 6 else swing_highs
    sl = swing_lows[-6:] if len(swing_lows) >= 6 else swing_lows

    if len(sh) >= 2 and abs(sh[-1]["y"] - sh[-2]["y"]) / sh[-2]["y"] < 0.02:
        patterns.append({"name": "Double Top", "signal": "BEARISH", "color": "#ef5350", "points": [{"x": sh[-2]["x"], "y": sh[-2]["y"]}, {"x": sh[-1]["x"], "y": sh[-1]["y"]}]})

    if len(sl) >= 2 and abs(sl[-1]["y"] - sl[-2]["y"]) / sl[-2]["y"] < 0.02:
        patterns.append({"name": "Double Bottom", "signal": "BULLISH", "color": "#26a69a", "points": [{"x": sl[-2]["x"], "y": sl[-2]["y"]}, {"x": sl[-1]["x"], "y": sl[-1]["y"]}]})

    if len(sh) >= 3:
        left, head, right = sh[-3], sh[-2], sh[-1]
        if head["y"] > left["y"] and head["y"] > right["y"] and abs(left["y"] - right["y"]) / left["y"] < 0.03:
            patterns.append({"name": "Head & Shoulders", "signal": "BEARISH", "color": "#ef5350", "points": [{"x": left["x"], "y": left["y"]}, {"x": head["x"], "y": head["y"]}, {"x": right["x"], "y": right["y"]}]})

    if len(sl) >= 3:
        left, head, right = sl[-3], sl[-2], sl[-1]
        if head["y"] < left["y"] and head["y"] < right["y"] and abs(left["y"] - right["y"]) / left["y"] < 0.03:
            patterns.append({"name": "Inv. Head & Shoulders", "signal": "BULLISH", "color": "#26a69a", "points": [{"x": left["x"], "y": left["y"]}, {"x": head["x"], "y": head["y"]}, {"x": right["x"], "y": right["y"]}]})

    if len(sh) >= 2 and len(sl) >= 2:
        if sh[-1]["y"] > sh[-2]["y"] and sl[-1]["y"] > sl[-2]["y"]:
            patterns.append({"name": "Uptrend (HH/HL)", "signal": "BULLISH", "color": "#26a69a", "points": []})
        if sh[-1]["y"] < sh[-2]["y"] and sl[-1]["y"] < sl[-2]["y"]:
            patterns.append({"name": "Downtrend (LH/LL)", "signal": "BEARISH", "color": "#ef5350", "points": []})
        if abs(sh[-1]["y"] - sh[-2]["y"]) / sh[-2]["y"] < 0.015 and sl[-1]["y"] > sl[-2]["y"]:
            patterns.append({"name": "Ascending Triangle", "signal": "BULLISH", "color": "#26a69a", "points": [{"x": sh[-2]["x"], "y": sh[-2]["y"]}, {"x": sh[-1]["x"], "y": sh[-1]["y"]}]})
        if abs(sl[-1]["y"] - sl[-2]["y"]) / sl[-2]["y"] < 0.015 and sh[-1]["y"] < sh[-2]["y"]:
            patterns.append({"name": "Descending Triangle", "signal": "BEARISH", "color": "#ef5350", "points": [{"x": sl[-2]["x"], "y": sl[-2]["y"]}, {"x": sl[-1]["x"], "y": sl[-1]["y"]}]})

    return patterns

def generate_chart(symbol="BNB", interval="4h", limit=60):
    symbol_pair = symbol.upper() + "USDT"
    candles = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol_pair, "interval": interval, "limit": limit}
    ).json()

    timestamps = [int(c[0]) for c in candles]
    opens  = [float(c[1]) for c in candles]
    highs  = [float(c[2]) for c in candles]
    lows   = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]

    ohlc_data = [{"x": timestamps[i], "o": opens[i], "h": highs[i], "l": lows[i], "c": closes[i]} for i in range(len(candles))]

    ema9  = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    rsi   = calculate_rsi(closes, 14)
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes, 20)
    swing_highs, swing_lows = find_swing_points(highs, lows, timestamps)
    patterns = detect_patterns(swing_highs, swing_lows)

    def fmt(arr):
        return [{"x": timestamps[i], "y": v} for i, v in enumerate(arr)]

    half = 1800000
    swing_high_dashes, swing_low_dashes = [], []
    for sh in swing_highs[-8:]:
        swing_high_dashes += [{"x": sh["x"]-half, "y": sh["y"]}, {"x": sh["x"]+half, "y": sh["y"]}, {"x": None, "y": None}]
    for sl in swing_lows[-8:]:
        swing_low_dashes += [{"x": sl["x"]-half, "y": sl["y"]}, {"x": sl["x"]+half, "y": sl["y"]}, {"x": None, "y": None}]

    support    = round(min(lows[-20:]), 4)
    resistance = round(max(highs[-20:]), 4)
    support_line    = [{"x": timestamps[0], "y": support},    {"x": timestamps[-1], "y": support}]
    resistance_line = [{"x": timestamps[0], "y": resistance}, {"x": timestamps[-1], "y": resistance}]
    rsi_70 = [{"x": timestamps[0], "y": 70}, {"x": timestamps[-1], "y": 70}]
    rsi_30 = [{"x": timestamps[0], "y": 30}, {"x": timestamps[-1], "y": 30}]

    current_rsi   = next((r for r in reversed(rsi) if r is not None), 50)
    current_price = closes[-1]
    trend = "BULLISH" if ema9[-1] and ema21[-1] and ema9[-1] > ema21[-1] else "BEARISH"
    rsi_signal = "Overbought" if current_rsi > 70 else "Oversold" if current_rsi < 30 else "Neutral"
    pattern_summary = f" | {patterns[-1]['name']}: {patterns[-1]['signal']}" if patterns else ""

    pattern_datasets = []
    for p in patterns:
        if p["points"]:
            pattern_datasets.append({
                "type": "line", "label": f"{p['name']} ({p['signal']})",
                "data": p["points"], "borderColor": p["color"],
                "borderWidth": 2, "borderDash": [8, 4],
                "pointRadius": 5, "fill": False,
                "spanGaps": False, "yAxisID": "y"
            })

    datasets = [
        {"label": f"{symbol}/USDT", "data": ohlc_data,
         "color": {"up": "#26a69a", "down": "#ef5350", "unchanged": "#999"},
         "borderColor": {"up": "#26a69a", "down": "#ef5350", "unchanged": "#999"}, "yAxisID": "y"},
        {"type": "line", "label": "EMA 9", "data": fmt(ema9), "borderColor": "#F0B90B", "borderWidth": 1.5, "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "y"},
        {"type": "line", "label": "EMA 21", "data": fmt(ema21), "borderColor": "#2196F3", "borderWidth": 1.5, "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "y"},
        {"type": "line", "label": "BB Upper", "data": fmt(bb_upper), "borderColor": "rgba(156,39,176,0.7)", "borderWidth": 1, "borderDash": [4,4], "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "y"},
        {"type": "line", "label": "BB Middle", "data": fmt(bb_middle), "borderColor": "rgba(156,39,176,0.4)", "borderWidth": 1, "borderDash": [2,2], "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "y"},
        {"type": "line", "label": "BB Lower", "data": fmt(bb_lower), "borderColor": "rgba(156,39,176,0.7)", "borderWidth": 1, "borderDash": [4,4], "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "y"},
        {"type": "line", "label": f"Support ${support}", "data": support_line, "borderColor": "#00e676", "borderWidth": 1.5, "borderDash": [6,3], "pointRadius": 0, "fill": False, "yAxisID": "y"},
        {"type": "line", "label": f"Resistance ${resistance}", "data": resistance_line, "borderColor": "#ff1744", "borderWidth": 1.5, "borderDash": [6,3], "pointRadius": 0, "fill": False, "yAxisID": "y"},
        {"type": "line", "label": "Swing Highs", "data": swing_high_dashes, "borderColor": "#ff6d00", "borderWidth": 2, "borderDash": [8,2], "pointRadius": 0, "fill": False, "spanGaps": False, "yAxisID": "y"},
        {"type": "line", "label": "Swing Lows", "data": swing_low_dashes, "borderColor": "#00e5ff", "borderWidth": 2, "borderDash": [8,2], "pointRadius": 0, "fill": False, "spanGaps": False, "yAxisID": "y"},
        {"type": "line", "label": f"RSI({round(current_rsi,1)}) {rsi_signal}", "data": fmt(rsi), "borderColor": "#e040fb", "borderWidth": 1.5, "pointRadius": 0, "fill": False, "spanGaps": True, "yAxisID": "rsi"},
        {"type": "line", "label": "RSI 70", "data": rsi_70, "borderColor": "rgba(255,23,68,0.5)", "borderWidth": 1, "borderDash": [4,4], "pointRadius": 0, "fill": False, "yAxisID": "rsi"},
        {"type": "line", "label": "RSI 30", "data": rsi_30, "borderColor": "rgba(0,230,118,0.5)", "borderWidth": 1, "borderDash": [4,4], "pointRadius": 0, "fill": False, "yAxisID": "rsi"},
    ] + pattern_datasets

    chart_config = {
        "type": "candlestick",
        "data": {"datasets": datasets},
        "options": {
            "plugins": {
                "title": {"display": True, "text": f"{symbol}/USDT {interval} | ${current_price} | {trend} | RSI:{round(current_rsi,1)}{pattern_summary}", "color": "#ffffff", "font": {"size": 13}},
                "legend": {"labels": {"color": "#ffffff", "fontSize": 10}}
            },
            "scales": {
                "x": {"type": "timeseries", "ticks": {"color": "#aaaaaa", "maxTicksLimit": 8}, "grid": {"color": "#2a2a2a"}},
                "y": {"position": "right", "ticks": {"color": "#aaaaaa"}, "grid": {"color": "#2a2a2a"}, "weight": 4},
                "rsi": {"position": "right", "min": 0, "max": 100, "ticks": {"color": "#e040fb", "stepSize": 20}, "grid": {"color": "#1a1a1a"}, "weight": 1}
            }
        }
    }

    response = requests.post(
        "https://quickchart.io/chart/create",
        json={"chart": chart_config, "backgroundColor": "#131722", "width": 1000, "height": 600, "version": 3}
    )
    return response.json().get("url", "Chart generation failed")

@app.route('/chart')
def chart():
    symbol   = request.args.get('symbol', 'BNB')
    interval = request.args.get('interval', '4h')
    try:
        url = generate_chart(symbol, interval)
        return jsonify({"url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5005, debug=False)
