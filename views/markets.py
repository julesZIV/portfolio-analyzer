from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from data.markets import MARKETS, MARKET_TICKERS, HEADLINE_TICKERS, SP500
from data.loader import market_prices, market_ohlc, latest_quotes
from analytics.risk import volatility, max_drawdown
from viz import charts
from viz.ui import REFRESH, assign_colors, chart
from views.profil import afficher_profil

NAMES = {t: v["name"] for t, v in MARKETS.items()}
TODAY = date.today()
PERIODS = {
    "YTD": date(TODAY.year, 1, 1),
    "1W": TODAY - timedelta(days=7),
    "1M": TODAY - timedelta(days=30),
    "3M": TODAY - timedelta(days=91),
    "1Y": TODAY - timedelta(days=365),
    "5Y": TODAY - timedelta(days=1826),
}


@st.cache_data(ttl=900, show_spinner="Loading markets…")
def history(start):
    prices = market_prices(MARKET_TICKERS, (start - timedelta(days=10)).isoformat(), complete=False)
    prices = prices[prices.index.dayofweek < 5]
    before = prices.index[prices.index.date < start]
    return prices.loc[before[-1]:] if len(before) else prices


@st.cache_data(ttl=900, show_spinner="Loading candles…")
def candles_history(ticker, start):
    return market_ohlc(ticker, start.isoformat())


@st.cache_data(ttl=55, show_spinner=False)
def quotes():
    return latest_quotes(MARKET_TICKERS)


def fmt(value, unit):
    if unit == "%":
        return f"{value:.2f}%"
    return f"{value:,.{4 if unit == '' else 2}f} {unit}".strip()


st.title("World markets")
afficher_profil()

@st.fragment(run_every=REFRESH)
def live_tiles():
    try:
        q = quotes()
    except Exception as e:
        st.error(f"Quotes unavailable: {e}")
        return
    st.caption(f"Live · updated {datetime.now():%H:%M:%S} · change vs previous close")
    columns = st.columns(4)
    for i, t in enumerate([t for t in HEADLINE_TICKERS if t in q.index]):
        columns[i % 4].metric(NAMES[t], fmt(q.loc[t, "last"], MARKETS[t]["unit"]), f"{q.loc[t, 'change']:+.2%}")


live_tiles()
st.divider()

period = st.radio("Period", list(PERIODS), horizontal=True, key="markets_period")

try:
    prices = history(PERIODS[period])
except Exception as e:
    st.error(f"Could not load price history: {e}")
    st.stop()

first = prices.apply(lambda s: s.dropna().iloc[0])
last = prices.apply(lambda s: s.dropna().iloc[-1])
perf = last / first - 1
perf_assets = perf.drop(["^TNX", "^VIX"], errors="ignore")

chart(
    f"Who is winning · {period}",
    charts.ranking(perf_assets, NAMES),
    "Every asset is converted to the same unit (% change) and sorted, so leaders and laggards are visible "
    "at a glance. Color only shows direction: blue is up, red is down.",
    f"{(perf_assets > 0).sum()} of {len(perf_assets)} assets are up. Best: {NAMES[perf_assets.idxmax()]} "
    f"({perf_assets.max():+.1%}). Worst: {NAMES[perf_assets.idxmin()]} ({perf_assets.min():+.1%}). "
    + (f"The S&P 500 is at {perf[SP500]:+.1%}." if SP500 in perf else ""),
)
st.divider()
selection = st.multiselect(
    "Compare markets", MARKET_TICKERS, default=["^GSPC", "^NDX", "^FCHI", "^N225"],
    format_func=lambda t: NAMES[t], max_selections=8, key="markets_selection",
)
if selection:
    base = prices[selection].ffill()
    perf_sel = perf[selection].sort_values()
    dd = max_drawdown(base)
    chart(
        "How they got there",
        charts.base_100(base, assign_colors(selection, "colors_markets"), NAMES),
        "The ranking shows the finish line, this shows the path. Rebasing everything to 100 puts an index at "
        "7,000 points and one at 60,000 on the same axis.",
        f"Best in this selection: {NAMES[perf_sel.index[-1]]} ({perf_sel.iloc[-1]:+.1%}). "
        f"Deepest drop along the way: {NAMES[dd.idxmin()]} ({dd.min():.1%} from its peak). "
        "Indices are in local currency.",
    )

st.divider()
focus = st.selectbox("Market in detail", MARKET_TICKERS, format_func=lambda t: NAMES[t], key="markets_focus")
try:
    ohlc = candles_history(focus, PERIODS[period])
except Exception as e:
    st.error(f"Could not load {NAMES[focus]}: {e}")
else:
    up_days = (ohlc["Close"] > ohlc["Open"]).mean()
    chart(
        f"{NAMES[focus]} day by day · {period}",
        charts.candles(ohlc, MARKETS[focus]["unit"] or "Rate"),
        "Each candle is one trading day: the body goes from open to close, the wicks show the day's high and low. "
        "Blue closed above its open, red below.",
        f"{up_days:.0%} of sessions closed up. Range over the period: "
        f"{fmt(ohlc['Low'].min(), MARKETS[focus]['unit'])} to {fmt(ohlc['High'].max(), MARKETS[focus]['unit'])}.",
    )

with st.expander("All markets"):
    filled = prices.ffill()
    table = pd.DataFrame({
        "Category": [MARKETS[t]["category"] for t in prices.columns],
        "Last": [fmt(last[t], MARKETS[t]["unit"]) for t in prices.columns],
        "Performance": perf,
        "Volatility": volatility(filled),
        "Max drawdown": max_drawdown(filled),
    }, index=prices.columns).rename(index=NAMES)
    st.dataframe(table.style.format({"Performance": "{:+.1%}", "Volatility": "{:.1%}", "Max drawdown": "{:.1%}"}),
                 width="stretch")

st.caption("Source: Yahoo Finance. Quotes can be delayed by up to 20 minutes.")
