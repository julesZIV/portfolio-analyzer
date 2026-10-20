from datetime import date, timedelta

import pandas as pd
import streamlit as st

from data.sec13f import INVESTORS, list_filings, filing_holdings, cusip_to_ticker, compare
from data.loader import market_prices, latest_quotes
from data.markets import SP500
from viz import charts
from viz.ui import chart
from views.profil import afficher_profil

TOP_N = 25


@st.cache_data(ttl=6 * 3600, show_spinner="Looking up SEC filings…")
def filings(cik):
    return list_filings(cik)


@st.cache_data(show_spinner="Reading the 13F filing…")
def holdings(cik, accession):
    df = filing_holdings(cik, accession)
    return df[df["option"] == ""].drop(columns="option"), df[df["option"] != ""]


@st.cache_data(show_spinner="Matching tickers…")
def tickers(cusips):
    return cusip_to_ticker(list(cusips))


@st.cache_data(ttl=900, show_spinner="Loading prices…")
def history(symbols, start):
    return market_prices(list(symbols) + [SP500], start, complete=False)


@st.cache_data(ttl=55, show_spinner=False)
def quotes(symbols):
    return latest_quotes(list(symbols))


def money(v):
    return f"${v / 1e9:,.1f}B" if v >= 1e9 else f"${v / 1e6:,.0f}M"


st.title("Famous investors")
afficher_profil()
investor = st.selectbox("Investor", list(INVESTORS), format_func=lambda n: f"{n} · {INVESTORS[n]['fund']}", key="investor")
cik = INVESTORS[investor]["cik"]

try:
    filing_list = filings(cik)
    if filing_list.empty:
        st.error("No 13F filing found for this fund.")
        st.stop()
    latest = filing_list.iloc[0]
    current, options = holdings(cik, latest["accession"])
    previous = holdings(cik, filing_list.iloc[1]["accession"])[0] if len(filing_list) > 1 else None
except Exception as e:
    st.error(f"Could not read SEC data: {e}")
    st.stop()

report_date, filing_date = latest["report_date"], latest["filing_date"]
age = (pd.Timestamp(date.today()) - filing_date).days
if age > 140:
    st.warning(f"The latest filing is {age} days old ({filing_date:%b %d, %Y}). This fund may have stopped filing.")

current = current.assign(weight=current["value"] / current["value"].sum())
current["ticker"] = current["cusip"].map(tickers(tuple(current["cusip"].head(TOP_N))))
current["label"] = [f"{i.title()} ({t})" if isinstance(t, str) else i.title()
                    for i, t in zip(current["issuer"], current["ticker"])]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio value", money(current["value"].sum()))
c2.metric("Positions", len(current))
c3.metric("Top 10 weight", f"{current['weight'].head(10).sum():.0%}")
c4.metric("As of", f"{report_date:%b %d, %Y}", help=f"Made public on {filing_date:%b %d, %Y}")
st.caption(
    "Source: the fund's latest quarterly 13F filing with the SEC. It lists US stock positions only "
    "(no shorts, no cash, no foreign stocks) and is published up to 45 days after quarter end."
    + (f" {len(options)} option position(s) ({', '.join((options['option'] + ' ' + options['issuer'].str.title()).head(4))}"
       f"{'…' if len(options) > 4 else ''}) are not counted." if len(options) else "")
)

tab_holdings, tab_changes, tab_copy = st.tabs(["Holdings", "Buys and sells", "Should you copy it?"])

with tab_holdings:
    n_half = int((current["weight"].cumsum() < 0.5).sum()) + 1
    chart(
        "Biggest positions",
        charts.top_holdings(current),
        "Sorted bars show what the portfolio really rests on. The long tail of small positions is grouped "
        "in gray so it does not dilute the picture.",
        f"{n_half} position(s) make up half of the portfolio, out of {len(current)}. "
        f"The largest is {current['label'].iloc[0]} at {current['weight'].iloc[0]:.1%}.",
    )
    with st.expander(f"Top {TOP_N} positions at today's prices"):
        top = current.head(TOP_N).dropna(subset=["ticker"])
        try:
            q = quotes(tuple(top["ticker"]))
            table = pd.DataFrame({
                "Position": top["label"].values,
                "Weight": top["weight"].values,
                "Shares": top["shares"].values,
                "Price": top["ticker"].map(q["last"]).values,
                "Today": top["ticker"].map(q["change"]).values,
            })
            st.dataframe(table.style.format({"Weight": "{:.1%}", "Shares": "{:,.0f}", "Price": "${:.2f}",
                                             "Today": "{:+.2%}"}, na_rep="–"), width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Quotes unavailable: {e}")

with tab_changes:
    if previous is None:
        st.info("Only one filing is available, so there is nothing to compare.")
    else:
        moves = compare(current, previous)
        counts = moves["action"].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("New", counts.get("New", 0))
        c2.metric("Sold", counts.get("Sold", 0))
        c3.metric("Added", counts.get("Added", 0))
        c4.metric("Reduced", counts.get("Reduced", 0))
        up, down = moves[moves["weight_change"] > 0].head(1), moves[moves["weight_change"] < 0].head(1)
        chart(
            f"Biggest changes · {filing_list.iloc[1]['report_date']:%b %Y} → {report_date:%b %Y}",
            charts.changes(moves),
            "What the investor decided this quarter says more than what they have held for years. Bars start "
            "at zero: blue gained weight, red lost weight. The action is written next to each name.",
            (f"Biggest increase: {up['issuer'].iloc[0].title()} ({up['weight_change'].iloc[0] * 100:+.1f} pts). "
             if len(up) else "")
            + (f"Biggest decrease: {down['issuer'].iloc[0].title()} ({down['weight_change'].iloc[0] * 100:+.1f} pts). "
               if len(down) else "")
            + "A weight can move from price changes alone, without any trade.",
        )
        with st.expander("All trades"):
            detail = moves[moves["action"] != "Unchanged"][
                ["issuer", "action", "shares_before", "shares", "shares_change", "weight_before", "weight"]]
            detail.columns = ["Issuer", "Action", "Shares before", "Shares after", "Shares change",
                              "Weight before", "Weight after"]
            st.dataframe(detail.style.format({
                "Shares before": "{:,.0f}", "Shares after": "{:,.0f}", "Shares change": "{:+.0%}",
                "Weight before": "{:.2%}", "Weight after": "{:.2%}"}, na_rep="–"), width="stretch", hide_index=True)

with tab_copy:
    copy = current.head(TOP_N).dropna(subset=["ticker"])
    try:
        prices = history(tuple(copy["ticker"]), (report_date - timedelta(days=7)).date().isoformat())
    except Exception as e:
        st.error(f"Prices unavailable: {e}")
        st.stop()

    start = prices.index[prices.index <= report_date]
    prices = prices.loc[start[-1]:] if len(start) else prices
    priced = [t for t in prices.columns if prices[t].notna().all()]
    copy = copy[copy["ticker"].isin(priced)]
    coverage = copy["value"].sum() / current["value"].sum()

    value = (prices[copy["ticker"]] * copy["shares"].values).sum(axis=1)
    portfolio = value / value.iloc[0] * 100
    sp = prices[SP500] / prices[SP500].iloc[0] * 100
    after = prices.index[prices.index >= filing_date]
    public = after[0] if len(after) else prices.index[-1]

    perf_quarter, sp_quarter = portfolio.iloc[-1] / 100 - 1, sp.iloc[-1] / 100 - 1
    perf_public = portfolio.iloc[-1] / portfolio.loc[public] - 1
    sp_public = sp.iloc[-1] / sp.loc[public] - 1

    c1, c2, c3 = st.columns(3)
    c1.metric("Since quarter end", f"{perf_quarter:+.1%}", f"{(perf_quarter - sp_quarter) * 100:+.1f} pts vs S&P 500")
    c2.metric("Since it became public", f"{perf_public:+.1%}", f"{(perf_public - sp_public) * 100:+.1f} pts vs S&P 500")
    c3.metric("Share of portfolio copied", f"{coverage:.0%}", help=f"Top {len(copy)} positions with a price.")

    chart(
        "Copied portfolio vs S&P 500",
        charts.copycat(portfolio, sp, "S&P 500", filing_date),
        "Tracks the declared positions (same share counts) against the S&P 500 from the quarter end. "
        "The dotted line is the day the filing became public: nobody could copy before it.",
        f"A copier could only buy on {filing_date:%b %d, %Y}. Since then the portfolio returned {perf_public:+.1%} "
        f"against {sp_public:+.1%} for the S&P 500. The investor may no longer hold these stocks. "
        "This is not investment advice.",
    )
