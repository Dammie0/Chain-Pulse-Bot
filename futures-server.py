#!/usr/bin/env python3
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

COIN_M_BASE = "https://dapi.binance.com"
USD_M_BASE  = "https://fapi.binance.com"
SPOT_BASE   = "https://api.binance.com"

def get_usdm_futures(symbol="BTC"):
    pair = symbol.upper() + "USDT"

    # Futures ticker
    ticker = requests.get(f"{USD_M_BASE}/fapi/v1/ticker/24hr", params={"symbol": pair}).json()

    # Spot price
    spot = requests.get(f"{SPOT_BASE}/api/v3/ticker/price", params={"symbol": pair}).json()

    # Funding rate
    funding = requests.get(f"{USD_M_BASE}/fapi/v1/fundingRate", params={"symbol": pair, "limit": 1}).json()

    # Open interest
    oi = requests.get(f"{USD_M_BASE}/fapi/v1/openInterest", params={"symbol": pair}).json()

    # Long/Short ratio
    lsr = requests.get(f"{USD_M_BASE}/futures/data/globalLongShortAccountRatio",
                       params={"symbol": pair, "period": "1h", "limit": 1}).json()

    # Top trader LSR
    top_lsr = requests.get(f"{USD_M_BASE}/futures/data/topLongShortAccountRatio",
                           params={"symbol": pair, "period": "1h", "limit": 1}).json()

    # Liquidations
    liquidations = requests.get(f"{USD_M_BASE}/fapi/v1/allForceOrders",
                                params={"symbol": pair, "limit": 5}).json()

    # Parse
    futures_price = float(ticker.get("lastPrice", 0))
    spot_price    = float(spot.get("price", 0))
    premium       = futures_price - spot_price
    premium_pct   = (premium / spot_price * 100) if spot_price else 0
    premium_type  = "Contango" if premium > 0 else "Backwardation"

    funding_rate = float(funding[0].get("fundingRate", 0)) * 100 if funding else 0
    funding_cost = "Longs pay shorts" if funding_rate > 0 else "Shorts pay longs"

    open_interest   = float(oi.get("openInterest", 0)) if isinstance(oi, dict) else 0
    oi_value        = open_interest * futures_price

    long_ratio  = float(lsr[0].get("longShortRatio", 1)) if lsr and isinstance(lsr, list) else 1
    long_pct    = round(long_ratio / (1 + long_ratio) * 100, 2)
    short_pct   = round(100 - long_pct, 2)

    top_long_ratio = float(top_lsr[0].get("longShortRatio", 1)) if top_lsr and isinstance(top_lsr, list) else 1
    top_long_pct   = round(top_long_ratio / (1 + top_long_ratio) * 100, 2)
    top_short_pct  = round(100 - top_long_pct, 2)

    liq_summary = []
    if isinstance(liquidations, list):
        for liq in liquidations[:5]:
            side  = liq.get("side", "")
            qty   = float(liq.get("origQty", 0))
            price = float(liq.get("price", 0))
            value = qty * price
            liq_summary.append({
                "side": "LONG liquidated" if side == "SELL" else "SHORT liquidated",
                "value": round(value, 2),
                "price": price
            })

    if long_pct > 60:
        sentiment = "Overcrowded Longs — contrarian BEARISH signal"
    elif short_pct > 60:
        sentiment = "Overcrowded Shorts — contrarian BULLISH signal"
    elif funding_rate > 0.05:
        sentiment = "High funding — longs overheated, caution"
    elif funding_rate < -0.05:
        sentiment = "Negative funding — shorts dominant, potential squeeze"
    else:
        sentiment = "Balanced — no extreme sentiment"

    return {
        "type": "USD-M Futures (USDT Settled)",
        "symbol": symbol.upper(),
        "pair": pair,
        "futures_price": round(futures_price, 2),
        "spot_price": round(spot_price, 2),
        "premium": round(premium, 2),
        "premium_pct": round(premium_pct, 4),
        "premium_type": premium_type,
        "funding_rate": round(funding_rate, 4),
        "funding_cost": funding_cost,
        "open_interest": round(open_interest, 2),
        "oi_value_usd": round(oi_value, 2),
        "long_pct": long_pct,
        "short_pct": short_pct,
        "top_trader_long": top_long_pct,
        "top_trader_short": top_short_pct,
        "sentiment": sentiment,
        "liquidations": liq_summary
    }

def get_coinm_futures(symbol="BTC"):
    pair = symbol.upper() + "USD"
    perp = f"{pair}_PERP"

    ticker   = requests.get(f"{COIN_M_BASE}/dapi/v1/ticker/24hr", params={"symbol": perp}).json()
    if isinstance(ticker, list): ticker = ticker[0] if ticker else {}

    spot     = requests.get(f"{SPOT_BASE}/api/v3/ticker/price", params={"symbol": f"{symbol.upper()}USDT"}).json()
    funding  = requests.get(f"{COIN_M_BASE}/dapi/v1/fundingRate", params={"symbol": perp, "limit": 1}).json()
    oi       = requests.get(f"{COIN_M_BASE}/dapi/v1/openInterest", params={"symbol": perp}).json()
    lsr      = requests.get(f"{COIN_M_BASE}/futures/data/globalLongShortAccountRatio", params={"pair": pair, "period": "1h", "limit": 1}).json()
    top_lsr  = requests.get(f"{COIN_M_BASE}/futures/data/topLongShortAccountRatio", params={"pair": pair, "period": "1h", "limit": 1}).json()
    liqs     = requests.get(f"{COIN_M_BASE}/dapi/v1/allForceOrders", params={"symbol": perp, "limit": 5}).json()

    futures_price = float(ticker.get("lastPrice", 0))
    spot_price    = float(spot.get("price", 0))
    premium       = futures_price - spot_price
    premium_pct   = (premium / spot_price * 100) if spot_price else 0
    premium_type  = "Contango" if premium > 0 else "Backwardation"

    funding_rate = float(funding[0].get("fundingRate", 0)) * 100 if funding else 0
    funding_cost = "Longs pay shorts" if funding_rate > 0 else "Shorts pay longs"

    open_interest = float(oi.get("openInterest", 0)) if isinstance(oi, dict) else 0
    oi_value      = open_interest * futures_price

    long_ratio = float(lsr[0].get("longAccount", 0)) * 100 if lsr and isinstance(lsr, list) else 0
    short_ratio = float(lsr[0].get("shortAccount", 0)) * 100 if lsr and isinstance(lsr, list) else 0
    top_long  = float(top_lsr[0].get("longAccount", 0)) * 100 if top_lsr and isinstance(top_lsr, list) else 0
    top_short = float(top_lsr[0].get("shortAccount", 0)) * 100 if top_lsr and isinstance(top_lsr, list) else 0

    liq_summary = []
    if isinstance(liqs, list):
        for liq in liqs[:5]:
            side  = liq.get("side", "")
            qty   = float(liq.get("origQty", 0))
            price = float(liq.get("price", 0))
            value = qty * price
            liq_summary.append({
                "side": "LONG liquidated" if side == "SELL" else "SHORT liquidated",
                "value": round(value, 2),
                "price": price
            })

    if long_ratio > 60:
        sentiment = "Overcrowded Longs — contrarian BEARISH signal"
    elif short_ratio > 60:
        sentiment = "Overcrowded Shorts — contrarian BULLISH signal"
    elif funding_rate > 0.05:
        sentiment = "High funding — longs overheated, caution"
    elif funding_rate < -0.05:
        sentiment = "Negative funding — shorts dominant, potential squeeze"
    else:
        sentiment = "Balanced — no extreme sentiment"

    return {
        "type": "COIN-M Futures (Crypto Settled)",
        "symbol": symbol.upper(),
        "pair": perp,
        "futures_price": round(futures_price, 2),
        "spot_price": round(spot_price, 2),
        "premium": round(premium, 2),
        "premium_pct": round(premium_pct, 4),
        "premium_type": premium_type,
        "funding_rate": round(funding_rate, 4),
        "funding_cost": funding_cost,
        "open_interest": round(open_interest, 2),
        "oi_value_usd": round(oi_value, 2),
        "long_pct": round(long_ratio, 2),
        "short_pct": round(short_ratio, 2),
        "top_trader_long": round(top_long, 2),
        "top_trader_short": round(top_short, 2),
        "sentiment": sentiment,
        "liquidations": liq_summary
    }

@app.route('/futures')
def futures():
    symbol    = request.args.get('symbol', 'BTC')
    type      = request.args.get('type', 'usdm').lower()
    try:
        if type == 'coinm':
            data = get_coinm_futures(symbol)
        else:
            data = get_usdm_futures(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5006, debug=False)

