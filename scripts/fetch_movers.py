"""Fetch market-wide top movers from Alpha Vantage's TOP_GAINERS_LOSERS endpoint.

NOT currently wired into fetch_all.py. Alpha Vantage's free-tier Terms of
Service (Section 2, "commercial use" definition, clause iii) classify
displaying this data on a public website — where visitors other than the API
key holder can see it — as commercial use, which requires contacting
premium@alphavantage.co rather than using the free "Get Free API Key" grant.
This module is kept for later, in case a proper display license is obtained.

That endpoint ranks the entire US market by day's percent change, but the raw
list is dominated by illiquid micro-caps and warrants spiking on trivial
volume — not meaningful "movers" for a professional audience. We filter to a
minimum price and minimum volume before taking the top few in each direction,
then look up company names via Finnhub (Alpha Vantage returns ticker only).
"""
import time
from typing import Optional

import requests

from config import ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY

TOP_GAINERS_LOSERS_URL = "https://www.alphavantage.co/query"
PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"
MIN_PRICE = 5.0
MIN_VOLUME = 1_000_000
TOP_N = 4
DELAY_SECONDS = 0.5


def _fetch_raw() -> Optional[dict]:
    try:
        resp = requests.get(
            TOP_GAINERS_LOSERS_URL,
            params={"function": "TOP_GAINERS_LOSERS", "apikey": ALPHA_VANTAGE_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "top_gainers" not in data or "top_losers" not in data:
            reason = data.get("Information") or data.get("Note") or data.get("Error Message") or data
            print(f"Fetching top movers... unexpected response: {reason}")
            return None
        return data
    except Exception as e:
        print(f"Fetching top movers... failed: {e}")
        return None


def _filter_liquid(rows: list) -> list:
    filtered = []
    for row in rows:
        try:
            price = float(row["price"])
            volume = int(row["volume"])
            pct = float(row["change_percentage"].rstrip("%"))
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if price >= MIN_PRICE and volume >= MIN_VOLUME:
            filtered.append({
                "symbol": row["ticker"],
                "price": price,
                "pct": pct,
                "volume": volume,
            })
    return filtered[:TOP_N]


def _fetch_company_name(symbol: str) -> Optional[str]:
    if not FINNHUB_API_KEY:
        return None
    try:
        resp = requests.get(PROFILE_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
        resp.raise_for_status()
        return resp.json().get("name") or None
    except Exception as e:
        print(f"  company name for {symbol} unavailable: {e}")
        return None


def fetch_movers() -> dict:
    if not ALPHA_VANTAGE_API_KEY:
        print("Fetching top movers... skipped (no ALPHA_VANTAGE_API_KEY set)")
        return {"gainers": [], "losers": []}

    raw = _fetch_raw()
    if not raw:
        return {"gainers": [], "losers": []}

    gainers = _filter_liquid(raw.get("top_gainers", []))
    losers = _filter_liquid(raw.get("top_losers", []))

    for item in gainers + losers:
        item["name"] = _fetch_company_name(item["symbol"]) or item["symbol"]
        time.sleep(DELAY_SECONDS)

    print(f"Fetching top movers... {len(gainers)} gainer(s), {len(losers)} loser(s) after liquidity filter ✓")
    return {"gainers": gainers, "losers": losers}


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_movers(), indent=2))
