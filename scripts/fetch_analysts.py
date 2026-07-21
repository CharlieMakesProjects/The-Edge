"""Fetch analyst ratings intelligence from Finnhub: consensus recommendation
trends (Strong Buy/Buy/Hold/Sell/Strong Sell) plus price targets, for each
tracked ticker.

Uses only free-tier Finnhub endpoints:
  - /stock/recommendation  monthly analyst recommendation counts
  - /stock/price-target    average/median/high/low analyst price target
  - /quote                 current price, used to compute implied upside/downside
"""
import time
from typing import Optional

import requests

from config import EARNINGS_TICKERS, FINNHUB_API_KEY, MEGACAP_SYMBOLS, WATCHLIST_SYMBOLS

RECOMMENDATION_URL = "https://finnhub.io/api/v1/stock/recommendation"
PRICE_TARGET_URL = "https://finnhub.io/api/v1/stock/price-target"
QUOTE_URL = "https://finnhub.io/api/v1/quote"
DELAY_SECONDS = 1.0

NAMES = {**WATCHLIST_SYMBOLS, **MEGACAP_SYMBOLS}


def _fetch_recommendation(symbol: str) -> Optional[dict]:
    try:
        resp = requests.get(RECOMMENDATION_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
        resp.raise_for_status()
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            return None

        latest = rows[0]
        strong_buy = latest.get("strongBuy") or 0
        buy = latest.get("buy") or 0
        hold = latest.get("hold") or 0
        sell = latest.get("sell") or 0
        strong_sell = latest.get("strongSell") or 0
        total = strong_buy + buy + hold + sell + strong_sell
        if total == 0:
            return None

        return {
            "period": latest.get("period"),
            "strong_buy": strong_buy,
            "buy": buy,
            "hold": hold,
            "sell": sell,
            "strong_sell": strong_sell,
            "total": total,
        }
    except Exception as e:
        print(f"  recommendation for {symbol} unavailable: {e}")
        return None


def _fetch_price_target(symbol: str) -> Optional[dict]:
    # Finnhub's free tier no longer includes this endpoint for all accounts
    # (some keys get a 403). Treat that the same as "no coverage" rather than
    # letting it take down the rest of the ticker's data.
    try:
        resp = requests.get(PRICE_TARGET_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
        resp.raise_for_status()
        row = resp.json()
        if not isinstance(row, dict) or not row.get("targetMean"):
            return None

        return {
            "high": row.get("targetHigh"),
            "low": row.get("targetLow"),
            "mean": row.get("targetMean"),
            "median": row.get("targetMedian"),
            "updated": row.get("lastUpdated"),
        }
    except Exception as e:
        print(f"  price target for {symbol} unavailable: {e}")
        return None


def _fetch_current_price(symbol: str) -> Optional[float]:
    try:
        resp = requests.get(QUOTE_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
        resp.raise_for_status()
        return resp.json().get("c") or None
    except Exception as e:
        print(f"  quote for {symbol} unavailable: {e}")
        return None


def fetch_analysts() -> dict:
    if not FINNHUB_API_KEY:
        print("Fetching analyst ratings... skipped (no FINNHUB_API_KEY set)")
        return {}

    analysts = {}
    for symbol in EARNINGS_TICKERS:
        try:
            ratings = _fetch_recommendation(symbol)
            time.sleep(DELAY_SECONDS)
            price_target = _fetch_price_target(symbol)
            time.sleep(DELAY_SECONDS)
            current_price = _fetch_current_price(symbol)
            time.sleep(DELAY_SECONDS)

            if not ratings and not price_target:
                print(f"Fetching analyst ratings for {symbol}... no coverage, skipped")
                continue

            upside_pct = None
            if price_target and price_target.get("mean") and current_price:
                upside_pct = round((price_target["mean"] - current_price) / current_price * 100, 2)

            analysts[symbol] = {
                "name": NAMES.get(symbol, symbol),
                "current_price": current_price,
                "ratings": ratings,
                "price_target": price_target,
                "upside_pct": upside_pct,
            }
            coverage = ratings["total"] if ratings else 0
            print(f"Fetching analyst ratings for {symbol}... {coverage} analyst(s), target={price_target.get('mean') if price_target else None} ✓")
        except Exception as e:
            print(f"Fetching analyst ratings for {symbol}... failed: {e}")

    return analysts


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_analysts(), indent=2))
