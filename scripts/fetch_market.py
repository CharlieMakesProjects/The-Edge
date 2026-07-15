"""Fetch equity quotes from Finnhub: market index proxies + watchlist tickers."""
import time
from typing import Optional

import requests

from config import FINNHUB_API_KEY, MARKET_SYMBOLS, WATCHLIST_SYMBOLS

QUOTE_URL = "https://finnhub.io/api/v1/quote"
DELAY_SECONDS = 0.5


def _fetch_quote(symbol: str, name: str) -> Optional[dict]:
    try:
        resp = requests.get(QUOTE_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
        resp.raise_for_status()
        q = resp.json()
        price = q.get("c")
        if not price:
            print(f"Fetching {symbol}... no data returned")
            return None
        print(f"Fetching {symbol}... ${price:,.2f} ✓")
        return {
            "price": price,
            "change": q.get("d"),
            "pct": q.get("dp"),
            "high": q.get("h"),
            "low": q.get("l"),
            "open": q.get("o"),
            "prev_close": q.get("pc"),
            "name": name,
        }
    except Exception as e:
        print(f"Fetching {symbol}... failed: {e}")
        return None


def fetch_market() -> dict:
    if not FINNHUB_API_KEY:
        print("Fetching market data... skipped (no FINNHUB_API_KEY set)")
        return {"market": {}, "watchlist": {}}

    market = {}
    for symbol, name in MARKET_SYMBOLS.items():
        quote = _fetch_quote(symbol, name)
        if quote:
            market[symbol] = quote
        time.sleep(DELAY_SECONDS)

    watchlist = {}
    for symbol, name in WATCHLIST_SYMBOLS.items():
        quote = _fetch_quote(symbol, name)
        if quote:
            watchlist[symbol] = quote
        time.sleep(DELAY_SECONDS)

    return {"market": market, "watchlist": watchlist}


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_market(), indent=2))
