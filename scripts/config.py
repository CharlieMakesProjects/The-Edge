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

DATA_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "market_data.json"
