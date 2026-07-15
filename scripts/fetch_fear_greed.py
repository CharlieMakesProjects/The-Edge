"""Fetch the crypto Fear & Greed Index from alternative.me (free, no API key)."""
from datetime import datetime, timezone

import requests

URL = "https://api.alternative.me/fng/?limit=30"


def fetch_fear_greed() -> dict:
    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
        entries = resp.json().get("data", [])
        if not entries:
            raise ValueError("empty response")

        history = []
        for entry in entries:
            date = datetime.fromtimestamp(int(entry["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
            history.append({
                "value": int(entry["value"]),
                "classification": entry["value_classification"],
                "date": date,
            })

        latest = history[0]
        print(f"Fetching Fear & Greed Index... {latest['value']} ({latest['classification']}) ✓")
        return {
            "value": latest["value"],
            "classification": latest["classification"],
            "history": history,
        }
    except Exception as e:
        print(f"Fetching Fear & Greed Index... failed: {e}")
        return {"value": None, "classification": None, "history": []}


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_fear_greed(), indent=2))
