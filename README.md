# The Edge

A free investment intelligence hub: a public landing page (`index.html`) that links to a live dashboard (`hub.html`) with 15 modules covering markets, crypto, insider trades, sector rotation, and more.

Market data is fetched by a Python pipeline (`scripts/`) and written to `data/market_data.json`, which `hub.html` loads on page load. A GitHub Actions workflow refreshes that file automatically twice on every trading day.

## Project structure

```
the-edge/
├── index.html                  Public landing page
├── hub.html                    The dashboard — reads data/market_data.json on load
├── data/market_data.json       Auto-generated snapshot, committed to the repo
├── scripts/
│   ├── fetch_all.py            Master script — runs every fetcher, writes the JSON
│   ├── fetch_market.py         Finnhub — S&P/Nasdaq/Dow proxies + watchlist quotes
│   ├── fetch_crypto.py         CoinGecko — BTC/ETH price + global market cap
│   ├── fetch_fear_greed.py     alternative.me — crypto Fear & Greed Index
│   ├── fetch_insiders.py       edgartools — SEC Form 4 insider trades
│   └── config.py               Reads API keys from env vars / .env
└── .github/workflows/update_data.yml   Scheduled + manual data refresh
```

## Local setup

```bash
git clone <your-repo-url>
cd the-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (never committed — it's in `.gitignore`):

```
FINNHUB_API_KEY=your_finnhub_key_here
EDGAR_IDENTITY=Your Name your.email@example.com
```

- **Finnhub key** — free at [finnhub.io](https://finnhub.io) (60 calls/min on the free tier). Without it, `fetch_market.py` skips gracefully and the market/watchlist sections in `hub.html` keep their fallback values.
- **EDGAR identity** — the SEC requires a real name + email on every EDGAR request. This isn't optional; without it `fetch_insiders.py` skips gracefully too. CoinGecko and alternative.me need no key at all.

Run the full pipeline:

```bash
python scripts/fetch_all.py
```

This prints progress for each fetcher and writes `data/market_data.json`. Any single fetcher failing (bad key, API outage) is caught and logged — the others still run, and the JSON always gets written.

Then open `hub.html` directly in a browser (or serve the folder, e.g. `python -m http.server`) to see it load live prices from that file.

## Deployment

1. Push this repo to GitHub.
2. In the repo's **Settings → Secrets and variables → Actions**, add two repository secrets: `FINNHUB_API_KEY` and `EDGAR_IDENTITY`.
3. The `Update Market Data` workflow (`.github/workflows/update_data.yml`) runs automatically at 9am and 5pm ET on weekdays, or on demand from the Actions tab (`workflow_dispatch`). Each run re-fetches all sources and commits `data/market_data.json` back to the repo if it changed.
4. Enable **GitHub Pages**: in **Settings → Pages**, set **Source** to "Deploy from a branch", pick the `main` branch and `/ (root)` folder, then save. Both `index.html` and `hub.html` are static files that read `data/market_data.json` at runtime via relative paths, so there's nothing to build — GitHub rebuilds the Pages site automatically on every push to `main`, including the bot commits from `update_data.yml`. The site is served at `https://<username>.github.io/<repo>/`, so all internal links (`hub.html`, `data/market_data.json`, etc.) must stay relative (no leading `/`) to resolve under that subpath.

## Notes

- `data/market_data.json` is committed to the repo so the site always has data to show, even if an API is briefly down.
- `hub.html` merges live data field-by-field onto its hardcoded fallback markup — any ticker or section missing from the JSON (e.g. Finnhub not configured yet) just keeps its original placeholder value instead of breaking.
- Finnhub calls are spaced 0.5s apart and CoinGecko calls 1s apart to stay well within free-tier rate limits.
- `fetch_insiders.py` is the slowest fetcher (10–30s) since it parses multiple SEC filings per ticker — that's expected.
