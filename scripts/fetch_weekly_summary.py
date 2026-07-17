"""Generate a 1-2 sentence "Key events this week" summary via the Claude API.

Condenses the freshly-fetched market_data.json (index moves, watchlist
movers, crypto, fear & greed, insider filings) into a short summary that
hub.html displays in the Key Events callout.
"""
import json

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, DATA_OUTPUT_PATH

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You write the \"Key events this week\" summary for a personal investing "
    "dashboard. Given the market data below, write 1-2 sentences covering the "
    "most notable index moves, watchlist movers, and sentiment shifts. Plain "
    "text, no markdown, no preamble — just the summary itself."
)


def _build_context(data: dict) -> str:
    lines = []

    market = data.get("market", {})
    moves = ", ".join(
        f"{sym} {q['pct']:+.2f}%" for sym, q in market.items() if q.get("pct") is not None
    )
    if moves:
        lines.append(f"Index moves today: {moves}.")

    watchlist = data.get("watchlist", {})
    movers = sorted(
        ((sym, q) for sym, q in watchlist.items() if q.get("pct") is not None),
        key=lambda kv: abs(kv[1]["pct"]),
        reverse=True,
    )[:5]
    if movers:
        lines.append(
            "Biggest watchlist movers: "
            + ", ".join(f"{sym} {q['pct']:+.2f}%" for sym, q in movers)
            + "."
        )

    crypto = data.get("crypto", {})
    btc, eth = crypto.get("BTC", {}), crypto.get("ETH", {})
    crypto_parts = []
    if btc.get("price") is not None:
        crypto_parts.append(f"BTC ${btc['price']:,.0f}")
    if eth.get("price") is not None:
        crypto_parts.append(f"ETH ${eth['price']:,.0f}")
    if crypto_parts:
        lines.append("Crypto: " + ", ".join(crypto_parts) + ".")

    fear_greed = data.get("fear_greed", {})
    if fear_greed.get("value") is not None:
        lines.append(
            f"Crypto Fear & Greed Index: {fear_greed['value']} ({fear_greed.get('classification')})."
        )

    insiders = data.get("insiders", [])
    tickers = sorted({i["ticker"] for i in insiders if i.get("ticker")})
    if tickers:
        lines.append("Recent insider Form 4 activity: " + ", ".join(tickers) + ".")

    return "\n".join(lines)


def fetch_weekly_summary(data: dict) -> str:
    if not ANTHROPIC_API_KEY:
        print("Fetching weekly summary... skipped (no ANTHROPIC_API_KEY set)")
        return ""

    context = _build_context(data)
    if not context:
        print("Fetching weekly summary... skipped (no market data to summarize)")
        return ""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        )
        summary = "".join(b.text for b in response.content if b.type == "text").strip()
        if not summary:
            print("Fetching weekly summary... empty response")
            return ""
        print(f"Fetching weekly summary... {summary[:70]}{'...' if len(summary) > 70 else ''} ✓")
        return summary
    except Exception as e:
        print(f"Fetching weekly summary... failed: {e}")
        return ""


def main():
    if not DATA_OUTPUT_PATH.exists():
        print(f"Fetching weekly summary... skipped ({DATA_OUTPUT_PATH} not found)")
        return

    with open(DATA_OUTPUT_PATH) as f:
        data = json.load(f)

    summary = fetch_weekly_summary(data)
    if not summary:
        return

    data["weekly_summary"] = summary
    with open(DATA_OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
