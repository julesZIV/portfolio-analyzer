# Portfolio Analyzer

A Streamlit app for financial analysis, organized in four pages:

- **World markets**: live quotes and performance for major indices, commodities, crypto and FX.
- **Famous investors**: portfolios of well-known investors, read from their SEC 13F filings.
- **My CAC 40 portfolio**: risk analysis and Markowitz optimization on CAC 40 stocks.
- **Options (Black-Scholes)**: option pricing, Greeks, implied volatility smile and volatility surface.

Built with Python, Streamlit, pandas, NumPy, SciPy and Plotly. Market data comes from Yahoo Finance.

## Features

### World markets
- Live quotes, refreshed every minute: US, European and Asian indices, gold, silver, oil, Bitcoin, Ethereum, EUR/USD, USD/JPY, US 10-year yield and VIX.
- Base-100 performance, drawdowns and candlestick charts over a chosen period.

### Famous investors
- Portfolios of 11 investors (Warren Buffett, Bill Ackman, Michael Burry, Ray Dalio…) pulled from their latest **13F** filings on SEC EDGAR.
- **Holdings**: top positions and their weight in the portfolio.
- **Buys and sells**: what changed since the previous quarter.
- **Should you copy it?**: how a portfolio that copied the fund on the day the filing went public would have performed.
- CUSIP identifiers are mapped to tickers with the OpenFIGI API and cached in `dataset/cusip_tickers.json`.

### My CAC 40 portfolio
- Pick up to 8 CAC 40 stocks and a period, from one week to five years.
- Live prices, base-100 performance against the CAC 40 index.
- Risk: annual return and volatility, Sharpe and Sortino ratios, beta, max drawdown, correlation matrix.
- **Markowitz optimization**: Monte Carlo cloud of random portfolios, efficient frontier, maximum-Sharpe and minimum-variance portfolios with their weights.

### Options (Black-Scholes)
- **Pricer**: call and put prices with the Black-Scholes model, extended to a continuous dividend yield `q` (Merton), plus vega and a price-versus-spot chart.
- **Real chain**: listed options for any ticker on Yahoo Finance. Implied volatility is solved with Newton-Raphson and plotted as a smile against Yahoo's values. The dividend yield can be implied from put-call parity, and quotes outside arbitrage bounds are flagged.
- **Vol surface**: 3D implied volatility surface across several expiries, built from out-of-the-money options.

## Getting started

```bash
git clone <repo-url>
cd portfolio-analyzer
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501.

## Tests

```bash
pip install pytest
python -m pytest src/test/test.py
```

## Project structure

```
portfolio-analyzer/
├── app.py                     # Streamlit entry point and page navigation
├── views/                     # one Streamlit page per file
│   ├── markets.py
│   ├── investors.py
│   ├── portfolio.py
│   ├── options.py
│   └── profil.py              # sidebar profile
├── src/
│   ├── analytics/             # financial computations
│   │   ├── black_scholes.py   # pricing, implied vol, Greeks, arbitrage bounds
│   │   ├── greeks.py
│   │   ├── optimization.py    # Markowitz, efficient frontier
│   │   ├── returns.py
│   │   └── risk.py            # volatility, Sharpe, Sortino, alpha, beta, drawdown
│   ├── data/                  # data sources
│   │   ├── loader.py          # Yahoo Finance download and cache
│   │   ├── markets.py         # tracked markets
│   │   ├── sec13f.py          # EDGAR 13F filings + OpenFIGI
│   │   └── universe.py        # CAC 40 constituents
│   ├── viz/                   # Plotly charts and UI helpers
│   └── test/
│       └── test.py
└── dataset/                   # local cache (CSV files are git-ignored)
```

## Data sources

- [Yahoo Finance](https://finance.yahoo.com) via `yfinance`: prices, quotes and option chains. Quotes can be delayed by up to 20 minutes.
- [SEC EDGAR](https://www.sec.gov/edgar): 13F filings.
- [OpenFIGI](https://www.openfigi.com): CUSIP → ticker mapping.
