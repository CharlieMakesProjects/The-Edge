"""Fetch recent SEC Form 4 insider trades for watchlist tickers via edgartools.

SEC requires a real identity string (name + email) on every request — this is
not optional, and requests without one get rejected.
"""
from datetime import datetime, timedelta, timezone

from config import EDGAR_IDENTITY, INSIDER_TICKERS

LOOKBACK_DAYS = 30
MAX_PER_TICKER = 5


def fetch_insiders() -> list:
    if not EDGAR_IDENTITY:
        print("Fetching insider signals... skipped (no EDGAR_IDENTITY set)")
        return []

    try:
        import edgar
    except ImportError:
        print("Fetching insider signals... skipped (edgartools not installed)")
        return []

    edgar.set_identity(EDGAR_IDENTITY)

    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    results = []

    for ticker in INSIDER_TICKERS:
        try:
            company = edgar.Company(ticker)
            filings = company.get_filings(form="4", filing_date=f"{since}:")
            count = 0
            for filing in filings:
                if count >= MAX_PER_TICKER:
                    break
                try:
                    form4 = filing.obj()
                    summary = form4.get_ownership_summary()
                    results.append({
                        "ticker": ticker,
                        "insider": summary.insider_name,
                        "position": summary.position,
                        "activity": summary.primary_activity,
                        "filing_date": str(filing.filing_date),
                    })
                    count += 1
                except Exception as inner_e:
                    print(f"  {ticker}: skipped one filing ({inner_e})")
            print(f"Fetching insider signals for {ticker}... {count} filing(s) ✓")
        except Exception as e:
            print(f"Fetching insider signals for {ticker}... failed: {e}")

    return results


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_insiders(), indent=2))
