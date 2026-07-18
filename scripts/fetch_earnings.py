"""Fetch earnings intelligence from Finnhub: historical EPS surprises (beat/miss
track record) plus the next confirmed earnings date, for each tracked ticker.

Uses only free-tier Finnhub endpoints:
  - /stock/earnings     historical actual vs. estimated EPS per quarter
  - /calendar/earnings  confirmed/estimated upcoming earnings date
"""
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from config import EARNINGS_TICKERS, FINNHUB_API_KEY, MEGACAP_SYMBOLS, WATCHLIST_SYMBOLS

EARNINGS_URL = "https://finnhub.io/api/v1/stock/earnings"
CALENDAR_URL = "https://finnhub.io/api/v1/calendar/earnings"
DELAY_SECONDS = 1.0
CALENDAR_LOOKAHEAD_DAYS = 180
MET_THRESHOLD_PCT = 0.5  # |surprise%| below this counts as "met" rather than beat/miss

NAMES = {**WATCHLIST_SYMBOLS, **MEGACAP_SYMBOLS}


def _classify(surprise_pct: Optional[float]) -> str:
    if surprise_pct is None:
        return "met"
    if surprise_pct > MET_THRESHOLD_PCT:
        return "beat"
    if surprise_pct < -MET_THRESHOLD_PCT:
        return "miss"
    return "met"


def _fetch_quarters(symbol: str) -> list:
    resp = requests.get(EARNINGS_URL, params={"symbol": symbol, "token": FINNHUB_API_KEY}, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    if not isinstance(rows, list):
        return []

    quarters = []
    for row in rows[:8]:
        surprise_pct = row.get("surprisePercent")
        quarters.append({
            "period": row.get("period"),
            "quarter": row.get("quarter"),
            "year": row.get("year"),
            "actual": row.get("actual"),
            "estimate": row.get("estimate"),
            "surprise_pct": surprise_pct,
            "result": _classify(surprise_pct),
        })
    return quarters


def _fetch_next_earnings_date(symbol: str) -> Optional[str]:
    today = datetime.now(timezone.utc).date()
    to = today + timedelta(days=CALENDAR_LOOKAHEAD_DAYS)
    resp = requests.get(
        CALENDAR_URL,
        params={"from": today.isoformat(), "to": to.isoformat(), "symbol": symbol, "token": FINNHUB_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    events = resp.json().get("earningsCalendar") or []
    upcoming = sorted(e["date"] for e in events if e.get("date") and e["date"] >= today.isoformat())
    return upcoming[0] if upcoming else None


def fetch_earnings() -> dict:
    if not FINNHUB_API_KEY:
        print("Fetching earnings intelligence... skipped (no FINNHUB_API_KEY set)")
        return {}

    earnings = {}
    for symbol in EARNINGS_TICKERS:
        try:
            quarters = _fetch_quarters(symbol)
            time.sleep(DELAY_SECONDS)
            next_date = _fetch_next_earnings_date(symbol)
            time.sleep(DELAY_SECONDS)

            if not quarters and not next_date:
                print(f"Fetching earnings for {symbol}... no data, skipped")
                continue

            recent = [q for q in quarters[:4] if q["surprise_pct"] is not None]
            avg_surprise_pct = round(sum(q["surprise_pct"] for q in recent) / len(recent), 2) if recent else None

            earnings[symbol] = {
                "name": NAMES.get(symbol, symbol),
                "next_earnings_date": next_date,
                "quarters": quarters,
                "avg_surprise_pct": avg_surprise_pct,
            }
            print(f"Fetching earnings for {symbol}... {len(quarters)} quarter(s), next={next_date} ✓")
        except Exception as e:
            print(f"Fetching earnings for {symbol}... failed: {e}")

    return earnings


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_earnings(), indent=2))
