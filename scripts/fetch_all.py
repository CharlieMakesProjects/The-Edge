"""Master script: runs every fetcher, combines results, writes data/market_data.json.

Each fetcher already catches its own errors and returns fallback data, but this
script wraps each call again so a fetcher raising an unexpected exception can
never take down the rest of the pipeline.
"""
import json
from datetime import datetime, timezone

from config import DATA_OUTPUT_PATH
from fetch_crypto import fetch_crypto
from fetch_earnings import fetch_earnings
from fetch_fear_greed import fetch_fear_greed
from fetch_insiders import fetch_insiders
from fetch_market import fetch_market
from fetch_weekly_summary import fetch_weekly_summary


def _safe_call(label, fn, fallback):
    try:
        return fn()
    except Exception as e:
        print(f"[fetch_all] {label} crashed unexpectedly: {e}")
        return fallback


def main():
    print("=== The Edge — data pipeline ===")

    market_data = _safe_call("fetch_market", fetch_market, {"market": {}, "megacap": {}, "watchlist": {}})
    crypto_data = _safe_call("fetch_crypto", fetch_crypto, {"BTC": {}, "ETH": {}, "XRP": {}, "total_market_cap": None})
    fear_greed_data = _safe_call("fetch_fear_greed", fetch_fear_greed, {"value": None, "classification": None, "history": []})
    insiders_data = _safe_call("fetch_insiders", fetch_insiders, [])
    earnings_data = _safe_call("fetch_earnings", fetch_earnings, {})

    combined = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "market": market_data.get("market", {}),
        "megacap": market_data.get("megacap", {}),
        "watchlist": market_data.get("watchlist", {}),
        "crypto": {
            "BTC": crypto_data.get("BTC", {}),
            "ETH": crypto_data.get("ETH", {}),
            "XRP": crypto_data.get("XRP", {}),
            "total_market_cap": crypto_data.get("total_market_cap"),
        },
        "fear_greed": fear_greed_data,
        "insiders": insiders_data,
        "earnings": earnings_data,
    }

    combined["weekly_summary"] = _safe_call(
        "fetch_weekly_summary", lambda: fetch_weekly_summary(combined), ""
    )

    DATA_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUTPUT_PATH, "w") as f:
        json.dump(combined, f, indent=2)

    print("\n=== Summary ===")
    print(f"Market indices:   {len(combined['market'])} fetched")
    print(f"Mega-cap stocks:  {len(combined['megacap'])} fetched")
    print(f"Watchlist stocks: {len(combined['watchlist'])} fetched")
    print(f"Crypto:           BTC={'ok' if combined['crypto']['BTC'].get('price') else 'missing'}, "
          f"ETH={'ok' if combined['crypto']['ETH'].get('price') else 'missing'}, "
          f"XRP={'ok' if combined['crypto']['XRP'].get('price') else 'missing'}")
    print(f"Fear & Greed:     {combined['fear_greed'].get('value')} ({combined['fear_greed'].get('classification')})")
    print(f"Insider filings:  {len(combined['insiders'])} found")
    print(f"Earnings:         {len(combined['earnings'])} ticker(s) fetched")
    print(f"Weekly summary:   {'ok' if combined['weekly_summary'] else 'missing'}")
    print(f"Written to:       {DATA_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
