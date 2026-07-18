"""Fetch BTC/ETH prices and global crypto market data from CoinGecko (free, no API key)."""
import time

import requests

PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum,ripple&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
)
GLOBAL_URL = "https://api.coingecko.com/api/v3/global"

COINS = {"bitcoin": "BTC", "ethereum": "ETH", "ripple": "XRP"}


def fetch_crypto() -> dict:
    result = {"BTC": {}, "ETH": {}, "XRP": {}, "total_market_cap": None}

    try:
        resp = requests.get(PRICE_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for coin_id, symbol in COINS.items():
            coin = data.get(coin_id, {})
            price = coin.get("usd")
            result[symbol] = {
                "price": price,
                "change_24h": round(coin.get("usd_24h_change", 0), 2) if coin.get("usd_24h_change") is not None else None,
                "market_cap": coin.get("usd_market_cap"),
            }
            print(f"Fetching {symbol}... ${price:,.2f} ✓" if price else f"Fetching {symbol}... failed")
    except Exception as e:
        print(f"Fetching BTC/ETH prices... failed: {e}")

    time.sleep(1)

    try:
        resp = requests.get(GLOBAL_URL, timeout=10)
        resp.raise_for_status()
        result["total_market_cap"] = resp.json().get("data", {}).get("total_market_cap", {}).get("usd")
        print("Fetching global crypto market cap... ✓")
    except Exception as e:
        print(f"Fetching global crypto market cap... failed: {e}")

    return result


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_crypto(), indent=2))
