"""Entry point for the Monday/Friday Hidden Gems refresh (see
.github/workflows/update_gems.yml). Read-modify-write against
data/market_data.json so it doesn't disturb whatever the twice-daily main
pipeline (fetch_all.py) last wrote there — the two workflows own different
keys in the same file.

Merges in the hand-written thesis text from data/gems_thesis.json by ticker.
A ticker with no entry there gets thesis: null, which the frontend renders
as a plain "not yet written" placeholder rather than fabricated prose.
"""
import json

from config import DATA_OUTPUT_PATH, GEMS_THESIS_PATH
from fetch_gems import fetch_gems


def _load_thesis() -> dict:
    if not GEMS_THESIS_PATH.exists():
        return {}
    with open(GEMS_THESIS_PATH) as f:
        return json.load(f)


def main():
    gems = fetch_gems()
    thesis = _load_thesis()
    for gem in gems:
        gem["thesis"] = thesis.get(gem["symbol"])

    data = {}
    if DATA_OUTPUT_PATH.exists():
        with open(DATA_OUTPUT_PATH) as f:
            data = json.load(f)

    data["hidden_gems"] = gems
    DATA_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    have_thesis = sum(1 for g in gems if g.get("thesis"))
    print(f"\nHidden gems: {len(gems)} pick(s) written to {DATA_OUTPUT_PATH} ({have_thesis} with thesis text)")


if __name__ == "__main__":
    main()
