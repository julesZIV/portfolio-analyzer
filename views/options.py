from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from analytics.black_scholes import black_scholes_price, vega, implied_volatility, borne_arbitrage
from viz import charts
from views.profil import afficher_profil


@st.cache_data(ttl=300)
def spot_and_rate(ticker):
    spot = float(yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1])
    rate = float(yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1]) / 100
    return spot, rate


@st.cache_data(ttl=3600)
def expiries(ticker):
    return list(yf.Ticker(ticker).options)


@st.cache_data(ttl=300)
def chain(ticker, expiry):
    ch = yf.Ticker(ticker).option_chain(expiry)
    return ch.calls, ch.puts


def implied_dividend(calls, puts, S, T, r):
    #q implicite par la parite call-put sur les strikes proches de la monnaie : C - P = S e^{-qT} - K e^{-rT}
    c = calls.set_index("strike"); p = puts.set_index("strike")
    quoted = [k for k in c.index.intersection(p.index)
              if min(c.bid[k], c.ask[k], p.bid[k], p.ask[k]) > 0]
    strikes = sorted(quoted, key=lambda k: abs(k - S))[:6]
    fwd = [(c.bid[k] + c.ask[k]) / 2 - (p.bid[k] + p.ask[k]) / 2 + k * np.exp(-r * T) for k in strikes]
    if not fwd or np.median(fwd) <= 0: #pas assez de cotations exploitables : on suppose q = 0
        return 0.0
    return -np.log(np.median(fwd) / S) / T

def echeance(ticker, expiry, S, r):
    calls, puts = chain(ticker, expiry)
    T = max(((datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days + 0.7) / 365, 1 / 365)
    q = implied_dividend(calls, puts, S, T, r)
    rows = []
    for typ, df in (("call", calls), ("put", puts)):
        df = df[(df.bid > 0) & (df.ask > 0)]
        for _, o in df.iterrows():
            mid = (o.bid + o.ask) / 2
            lo, hi = borne_arbitrage(S, o.strike, T, r, mid, typ, q)
            rows.append(dict(type=typ, strike=o.strike, bid=o.bid, ask=o.ask, mid=mid,
                             iv=implied_volatility(S, o.strike, T, r, mid, typ, q), iv_yahoo=o.impliedVolatility,
                             in_bounds=lo <= mid <= hi, T=T))
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def surface_points(ticker, n_expiries, width, min_days=7):
    S, r = spot_and_rate(ticker)
    now = datetime.now()
    exps = [e for e in expiries(ticker) if (datetime.strptime(e, "%Y-%m-%d") - now).days >= min_days][:n_expiries]
    df = pd.concat([echeance(ticker, e, S, r) for e in exps], ignore_index=True)
    #options OTM uniquement : puts sous le spot, calls au-dessus (plus liquides, pas de doublon par strike)
    otm = ((df.type == "put") & (df.strike < S)) | ((df.type == "call") & (df.strike >= S))
    df = df[otm & df.in_bounds & (df.strike > (1 - width) * S) & (df.strike < (1 + width) * S)].dropna(subset=["iv"])
    df["moneyness"] = df.strike / S
    return df, S

st.title("Options (Black-Scholes)")
pricer, real, surface = st.tabs(["Pricer", "Real chain", "Vol surface"])
afficher_profil()
with pricer:
    c1, c2, c3 = st.columns(3)
    S = c1.number_input("Underlying price S", value=100.0, min_value=0.01)
    K = c1.number_input("Strike K", value=100.0, min_value=0.01)
    T = c2.number_input("Maturity T (years)", value=0.5, min_value=0.01, step=0.05)
    r = c2.number_input("Risk-free rate r", value=0.03, step=0.005, format="%.3f")
    sigma = c3.number_input("Volatility sigma", value=0.20, min_value=0.01, step=0.01)
    q = c3.number_input("Dividend yield q", value=0.0, step=0.005, format="%.3f")

    call = black_scholes_price(S, K, T, r, sigma, "call", q)
    put = black_scholes_price(S, K, T, r, sigma, "put", q)
    m1, m2, m3 = st.columns(3)
    m1.metric("Call", f"{call:.2f}")
    m2.metric("Put", f"{put:.2f}")
    m3.metric("Vega (per +1 vol pt)", f"{vega(S, K, T, r, sigma, q) / 100:.3f}")

    spots = np.linspace(0.5 * K, 1.5 * K, 200)
    st.plotly_chart(charts.option_prices(spots, black_scholes_price(spots, K, T, r, sigma, "call", q),  black_scholes_price(spots, K, T, r, sigma, "put", q), S, K),
                    width="stretch")

with surface:
    c1, c2, c3 = st.columns(3)
    ticker_s = c1.text_input("Ticker", value="SPY", key="surface_ticker").strip().upper()
    n_exp = c2.slider("Number of expiries", 3, 15, 8)
    width_s = c3.slider("Strikes around spot (%)", 5, 50, 20, key="surface_width") / 100
    #pas de st.stop() ici : il couperait aussi le rendu de l'onglet "chaine reelle"
    try:
        pts, S_s = surface_points(ticker_s, n_exp, width_s)
    except Exception as e:
        pts, S_s = None, None
        st.write("Error:", e)
    if pts is not None and (pts["T"].nunique() < 2 or len(pts) < 10):
        st.write("Not enough points to build a surface")
    elif pts is not None:
        st.plotly_chart(charts.vol_surface(pts), width="stretch")
        st.caption(f"{len(pts)} OTM options across {pts['T'].nunique()} expiries, linear interpolation between market points. "
                   f"Spot: {S_s:.2f}")

with real:
    c1, c2, c3 = st.columns(3)
    ticker = c1.text_input("Ticker", value="SPY").strip().upper()
    try:
        exps = expiries(ticker)
        S, r = spot_and_rate(ticker)
    except Exception as e:
        st.write("Error:", e)
        st.stop()
    if not exps:
        st.write("No listed options for this ticker")
        st.stop()

    now = datetime.now()
    default = min(range(len(exps)), key=lambda i: abs((datetime.strptime(exps[i], "%Y-%m-%d") - now).days - 30))
    expiry = c2.selectbox("Expiry", exps, index=default)
    width = c3.slider("Strikes around spot (%)", 5, 30, 10) / 100
    q_mode = c3.radio("Dividend yield q", ["Implied (parity)", "0"], horizontal=True)

    T = max(((datetime.strptime(expiry, "%Y-%m-%d") - now).days + 0.7) / 365, 1 / 365)
    calls, puts = chain(ticker, expiry)
    q = implied_dividend(calls, puts, S, T, r) if q_mode.startswith("Implied") else 0.0

    rows = []
    for typ, df in (("call", calls), ("put", puts)):
        df = df[(df.strike > (1 - width) * S) & (df.strike < (1 + width) * S) & (df.bid > 0) & (df.ask > 0)]
        for _, o in df.iterrows():
            mid = (o.bid + o.ask) / 2
            lo, hi = borne_arbitrage(S, o.strike, T, r, mid, typ, q)
            rows.append(dict(type=typ, strike=o.strike, bid=o.bid, ask=o.ask, mid=mid, iv=implied_volatility(S, o.strike, T, r, mid, typ, q), iv_yahoo=o.impliedVolatility, in_bounds=lo <= mid <= hi))
    res = pd.DataFrame(rows)
    if res.empty:
        st.write("No options with a bid/ask in this range")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Spot", f"{S:.2f}")
    m2.metric("Rate r (^IRX)", f"{r:.2%}")
    m3.metric("Dividend yield q", f"{q:.2%}")
    m4.metric("Outside arbitrage bounds", f"{(~res.in_bounds).sum()} / {len(res)}")

    st.plotly_chart(charts.vol_smile(res[res.in_bounds], S), width="stretch")
    st.caption("Implied q = dividend + timing gap between the closing price and the option quotes. "
               "US equity options are American and can be exercised before expiry, which Black-Scholes ignores.")

    with st.expander("Table"):
        st.dataframe(res.style.format({"bid": "{:.2f}", "ask": "{:.2f}", "mid": "{:.2f}", "iv": "{:.2%}", "iv_yahoo": "{:.2%}"}, na_rep="–"), width="stretch")
