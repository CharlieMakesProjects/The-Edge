"""Hidden Gems screener: ranks a fixed candidate universe (config.GEMS_CANDIDATES)
by real, free Finnhub fundamentals. Only refreshed on the Mon/Fri schedule
(.github/workflows/update_gems.yml) — much slower than the twice-daily main
pipeline by design, per the requirement that this section update ~2x/week
rather than every run.

Two entry points:
  - update_price_history()  cheap (1 quote call/candidate); called every
                             pipeline run via fetch_all.py to build up daily
                             closes for RSI/EMA over time — see price_history.py.
  - fetch_gems()             expensive (profile+metric+peers+recommendation
                             per candidate, ~5 calls each); called only by
                             the Mon/Fri workflow via update_gems.py. Ranks
                             candidates by composite percentile score across
                             P/E-vs-peers, revenue growth, EPS growth, and
                             analyst consensus, returns the top GEMS_TOP_N.

No thesis text ("why undervalued" / "catalyst") or source link is generated
here — those stay hand-written in data/gems_thesis.json, merged in by
update_gems.py. A newly-ranked symbol with no entry there is left for the
frontend to show a plain placeholder, never fabricated prose or a guessed URL.
"""
import time
from datetime import datetime, timezone
from statistics import mean, median
from typing import Optional

import requests

from config import FINNHUB_API_KEY, GEMS_CANDIDATES, GEMS_TOP_N
from price_history import compute_ema, compute_rsi, load_history, update_history

QUOTE_URL = "https://finnhub.io/api/v1/quote"
PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"
METRIC_URL = "https://finnhub.io/api/v1/stock/metric"
PEERS_URL = "https://finnhub.io/api/v1/stock/peers"
RECOMMENDATION_URL = "https://finnhub.io/api/v1/stock/recommendation"
DELAY_SECONDS = 1.0  # free tier is 60 calls/min; 1 call/sec stays at the edge safely
MAX_PEERS = 5


def _get(url: str, params: dict, timeout: int = 10) -> dict:
    resp = requests.get(url, params={**params, "token": FINNHUB_API_KEY}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _fetch_quote_price(symbol: str) -> Optional[float]:
    try:
        return _get(QUOTE_URL, {"symbol": symbol}).get("c") or None
    except Exception as e:
        print(f"  quote for {symbol} unavailable: {e}")
        return None


def update_price_history() -> None:
    if not FINNHUB_API_KEY:
        print("Updating gems price history... skipped (no FINNHUB_API_KEY set)")
        return
    prices = {}
    for symbol in GEMS_CANDIDATES:
        prices[symbol] = _fetch_quote_price(symbol)
        time.sleep(DELAY_SECONDS)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update_history(prices, today)
    have = sum(1 for p in prices.values() if p is not None)
    print(f"Updating gems price history... {have}/{len(GEMS_CANDIDATES)} price(s) recorded for {today} ✓")


def _fetch_profile(symbol: str) -> dict:
    try:
        return _get(PROFILE_URL, {"symbol": symbol})
    except Exception as e:
        print(f"  profile for {symbol} unavailable: {e}")
        return {}


def _fetch_metric(symbol: str) -> dict:
    try:
        return _get(METRIC_URL, {"symbol": symbol, "metric": "all"}).get("metric", {})
    except Exception as e:
        print(f"  metrics for {symbol} unavailable: {e}")
        return {}


def _fetch_peers(symbol: str) -> list:
    try:
        peers = _get(PEERS_URL, {"symbol": symbol})
        if not isinstance(peers, list):
            return []
        return [p for p in peers if isinstance(p, str) and p != symbol][:MAX_PEERS]
    except Exception as e:
        print(f"  peers for {symbol} unavailable: {e}")
        return []


def _fetch_recommendation(symbol: str) -> Optional[dict]:
    try:
        rows = _get(RECOMMENDATION_URL, {"symbol": symbol})
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
            "strong_buy": strong_buy, "buy": buy, "hold": hold,
            "sell": sell, "strong_sell": strong_sell, "total": total,
        }
    except Exception as e:
        print(f"  recommendation for {symbol} unavailable: {e}")
        return None


MAX_SANE_PE = 200  # a P/E beyond this reflects near-zero earnings, not a
                    # usable valuation signal — treat as absent rather than
                    # let one outlier distort a peer average for someone else


def _pe(metric: dict) -> Optional[float]:
    for key in ("peTTM", "peExclExtraTTM", "peBasicExclExtraTTM", "peNormalizedAnnual"):
        val = metric.get(key)
        if val is not None and 0 < val <= MAX_SANE_PE:
            return val
    return None


def _percentile_ranks(values: dict) -> dict:
    """symbol->value to symbol->percentile rank in [0,1], higher is better.
    Symbols with a None value are simply excluded from that metric's ranking
    rather than penalized with a guessed value."""
    present = {s: v for s, v in values.items() if v is not None}
    if len(present) < 2:
        return {s: 0.5 for s in present}
    ordered = sorted(present, key=lambda s: present[s])
    n = len(ordered)
    return {s: i / (n - 1) for i, s in enumerate(ordered)}


def fetch_gems() -> list:
    if not FINNHUB_API_KEY:
        print("Fetching hidden gems... skipped (no FINNHUB_API_KEY set)")
        return []

    history = load_history()
    peer_metric_cache = {}
    candidates = {}

    for symbol in GEMS_CANDIDATES:
        profile = _fetch_profile(symbol)
        time.sleep(DELAY_SECONDS)
        metric = _fetch_metric(symbol)
        time.sleep(DELAY_SECONDS)
        peers = _fetch_peers(symbol)
        time.sleep(DELAY_SECONDS)
        recommendation = _fetch_recommendation(symbol)
        time.sleep(DELAY_SECONDS)
        price = _fetch_quote_price(symbol)
        time.sleep(DELAY_SECONDS)

        if not metric or price is None:
            print(f"Screening {symbol}... insufficient data, skipped")
            continue

        pe = _pe(metric)

        peer_pes = []
        for peer in peers:
            if peer not in peer_metric_cache:
                peer_metric_cache[peer] = _fetch_metric(peer)
                time.sleep(DELAY_SECONDS)
            peer_pe = _pe(peer_metric_cache[peer])
            if peer_pe is not None:
                peer_pes.append(peer_pe)
        # Median, not mean — robust to a single peer with an outlier P/E.
        peer_avg_pe = round(median(peer_pes), 2) if peer_pes else None
        pe_vs_peers_pct = (
            round((peer_avg_pe - pe) / peer_avg_pe * 100, 1)
            if pe is not None and peer_avg_pe else None
        )

        closes = [e["price"] for e in history.get(symbol, [])]
        rsi14 = compute_rsi(closes)
        ema50 = compute_ema(closes)

        analyst_buy_pct = (
            round((recommendation["strong_buy"] + recommendation["buy"]) / recommendation["total"] * 100, 1)
            if recommendation else None
        )

        candidates[symbol] = {
            "symbol": symbol,
            "name": profile.get("name") or symbol,
            "sector": profile.get("finnhubIndustry"),
            "price": price,
            "pe": pe,
            "pe_vs_peers_pct": pe_vs_peers_pct,
            "revenue_growth_ttm": metric.get("revenueGrowthTTMYoy"),
            "eps_growth_ttm": metric.get("epsGrowthTTMYoy"),
            "analyst_buy_pct": analyst_buy_pct,
            "analyst_counts": recommendation,
            "rsi14": rsi14,
            "ema50": ema50,
        }
        print(f"Screening {symbol}... P/E {pe}, rev growth {metric.get('revenueGrowthTTMYoy')}% ✓")

    # Composite score = average percentile rank across whichever metrics are
    # actually available for each candidate (never fills gaps with a guess).
    rank_inputs = {
        "revenue_growth_ttm": {s: c["revenue_growth_ttm"] for s, c in candidates.items()},
        "eps_growth_ttm": {s: c["eps_growth_ttm"] for s, c in candidates.items()},
        "pe_vs_peers_pct": {s: c["pe_vs_peers_pct"] for s, c in candidates.items()},
        "analyst_buy_pct": {s: c["analyst_buy_pct"] for s, c in candidates.items()},
    }
    rank_maps = {k: _percentile_ranks(v) for k, v in rank_inputs.items()}

    for symbol, c in candidates.items():
        ranks = [rank_maps[k][symbol] for k in rank_maps if symbol in rank_maps[k]]
        c["score"] = round(mean(ranks), 4) if ranks else 0.0

    ranked = sorted(candidates.values(), key=lambda c: c["score"], reverse=True)
    top = ranked[:GEMS_TOP_N]
    print(f"Fetching hidden gems... ranked {len(candidates)} candidate(s), selected top {len(top)} ✓")
    return top


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_gems(), indent=2))
