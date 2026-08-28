"""Rolling daily closing-price history, used to compute real RSI/EMA for the
Hidden Gems screener without a paid historical-data API.

Finnhub's free tier doesn't include historical daily candles (confirmed:
/stock/candle returns 403 on the free key), so there's no free source of
past prices to backfill from. Instead this file is grown incrementally by
the regular twice-daily pipeline (fetch_all.py calls update_history() every
run), independent of how often the Hidden Gems ranking itself refreshes.
RSI(14) needs ~15 trading days of history; EMA(50) needs ~50 — both will
read as None until enough days have accumulated.
"""
import json

from config import PRICE_HISTORY_PATH

MAX_ENTRIES = 120  # comfortably covers a 50-day EMA plus warmup


def load_history() -> dict:
    if not PRICE_HISTORY_PATH.exists():
        return {}
    with open(PRICE_HISTORY_PATH) as f:
        return json.load(f)


def update_history(prices: dict, today: str) -> None:
    """Upsert today's price per symbol; a same-day rerun overwrites rather
    than duplicates, so the second (after-close) run of a day wins."""
    history = load_history()
    for symbol, price in prices.items():
        if price is None:
            continue
        entries = history.setdefault(symbol, [])
        entries[:] = [e for e in entries if e["date"] != today]
        entries.append({"date": today, "price": price})
        entries.sort(key=lambda e: e["date"])
        del entries[:-MAX_ENTRIES]
    PRICE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRICE_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def compute_rsi(closes: list, period: int = 14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def compute_ema(closes: list, period: int = 50):
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period  # seed with SMA of the first window
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)
