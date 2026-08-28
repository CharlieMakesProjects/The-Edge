"""Central config: reads API keys/settings from environment variables.

Locally, python-dotenv loads a .env file (gitignored) into the environment.
In GitHub Actions, the same variable names are injected from repo secrets,
so no code path differs between local and CI runs.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
EDGAR_IDENTITY = os.environ.get("EDGAR_IDENTITY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")  # unused for now; fetch_movers.py is not wired into fetch_all.py — see its docstring

# Symbols fetched from Finnhub
MARKET_SYMBOLS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq-100",
    "DIA": "Dow Jones",
}

# Mega-cap stocks fetched from Finnhub, used by the ticker tape
MEGACAP_SYMBOLS = {
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "TSLA": "Tesla",
}

WATCHLIST_SYMBOLS = {
    "CRWV": "CoreWeave",
    "RIOT": "Riot Platforms",
    "BE": "Bloom Energy",
    "CEG": "Constellation Energy",
    "CCJ": "Cameco",
    "RKLB": "Rocket Lab",
    "MU": "Micron Technology",
    "CLSK": "CleanSpark",
    "OPFI": "OppFi",
    "TJX": "TJX Companies",
    "CTRE": "CareTrust REIT",
}

# Tickers checked for SEC Form 4 insider activity
INSIDER_TICKERS = ["CRWV", "RIOT", "BE", "MU", "CLSK", "CEG", "CCJ"]

# Tickers checked for earnings history + upcoming earnings date
EARNINGS_TICKERS = [
    "CRWV", "RIOT", "BE", "MU", "CLSK", "CEG", "CCJ",
    "AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "TSLA",
]

# Fixed candidate universe for the "Hidden gems" screener (fetch_gems.py) —
# union of the tracked watchlist, the sector-thesis tickers listed in
# hub.html's sector research sections (nuclear/space/REIT/defense/biotech),
# and the two tickers (TKR, RBC) already shown as static gems picks but not
# listed anywhere else. Everything here is a ticker already curated somewhere
# in the app; nothing new is being introduced.
GEMS_CANDIDATES = sorted(set(WATCHLIST_SYMBOLS) | {
    "CEG", "CCJ", "BWXT", "OKLO",  # nuclear
    "RKLB", "VOYG", "PL", "AVAV",  # space & defense
    "WELL", "CTRE", "OHI", "VTR",  # senior housing REITs
    "LHX",                         # defense tech
    "ARE",                         # biotech
    "TKR", "RBC",                  # existing static gems picks (industrial)
})
GEMS_TOP_N = 6

DATA_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.json"
GEMS_THESIS_PATH = Path(__file__).resolve().parent.parent / "data" / "gems_thesis.json"
PRICE_HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "price_history.json"
