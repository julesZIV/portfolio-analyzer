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
    strikes = sorted(c.index.intersection(p.index), key=lambda k: abs(k - S))[:6]
    fwd = [(c.bid[k] + c.ask[k]) / 2 - (p.bid[k] + p.ask[k]) / 2 + k * np.exp(-r * T) for k in strikes]
    return -np.log(np.median(fwd) / S) / T


st.title("options black-scholes")
pricer, real = st.tabs(["pricer", "chaine reelle"])
afficher_profil()
with pricer:
    c1, c2, c3 = st.columns(3)
    S = c1.number_input("prix du sous-jacent S", value=100.0, min_value=0.01)
    K = c1.number_input("strike K", value=100.0, min_value=0.01)
    T = c2.number_input("maturite T (annees)", value=0.5, min_value=0.01, step=0.05)
    r = c2.number_input("taux sans risque r", value=0.03, step=0.005, format="%.3f")
    sigma = c3.number_input("volatilite sigma", value=0.20, min_value=0.01, step=0.01)
    q = c3.number_input("dividende q", value=0.0, step=0.005, format="%.3f")

    call = black_scholes_price(S, K, T, r, sigma, "call", q)
    put = black_scholes_price(S, K, T, r, sigma, "put", q)
    m1, m2, m3 = st.columns(3)
    m1.metric("call", f"{call:.2f}")
    m2.metric("put", f"{put:.2f}")
    m3.metric("vega (pour +1 pt de vol)", f"{vega(S, K, T, r, sigma, q) / 100:.3f}")

    spots = np.linspace(0.5 * K, 1.5 * K, 200)
    st.plotly_chart(charts.option_prices(spots, black_scholes_price(spots, K, T, r, sigma, "call", q),  black_scholes_price(spots, K, T, r, sigma, "put", q), S, K),
                    width="stretch")

with real:
    c1, c2, c3 = st.columns(3)
    ticker = c1.text_input("ticker", value="SPY").strip().upper()
    try:
        exps = expiries(ticker)
        S, r = spot_and_rate(ticker)
    except Exception as e:
        st.write("erreur :", e)
        st.stop()
    if not exps:
        st.write("pas d'options cotees pour ce ticker")
        st.stop()

    now = datetime.now()
    default = min(range(len(exps)), key=lambda i: abs((datetime.strptime(exps[i], "%Y-%m-%d") - now).days - 30))
    expiry = c2.selectbox("echeance", exps, index=default)
    width = c3.slider("strikes autour du spot (%)", 5, 30, 10) / 100
    q_mode = c3.radio("dividende q", ["implicite (parite)", "0"], horizontal=True)

    T = max(((datetime.strptime(expiry, "%Y-%m-%d") - now).days + 0.7) / 365, 1 / 365)
    calls, puts = chain(ticker, expiry)
    q = implied_dividend(calls, puts, S, T, r) if q_mode.startswith("implicite") else 0.0

    rows = []
    for typ, df in (("call", calls), ("put", puts)):
        df = df[(df.strike > (1 - width) * S) & (df.strike < (1 + width) * S) & (df.bid > 0) & (df.ask > 0)]
        for _, o in df.iterrows():
            mid = (o.bid + o.ask) / 2
            lo, hi = borne_arbitrage(S, o.strike, T, r, mid, typ, q)
            rows.append(dict(type=typ, strike=o.strike, bid=o.bid, ask=o.ask, mid=mid, iv=implied_volatility(S, o.strike, T, r, mid, typ, q), iv_yahoo=o.impliedVolatility, in_bounds=lo <= mid <= hi))
    res = pd.DataFrame(rows)
    if res.empty:
        st.write("aucune option avec bid/ask sur cette plage")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("spot", f"{S:.2f}")
    m2.metric("taux r (^IRX)", f"{r:.2%}")
    m3.metric("dividende q", f"{q:.2%}")
    m4.metric("hors bornes d'arbitrage", f"{(~res.in_bounds).sum()} / {len(res)}")

    st.plotly_chart(charts.vol_smile(res[res.in_bounds], S), width="stretch")
    st.caption("q implicite = dividende + decalage horaire entre le cours de cloture et les cotations d'options. "
               "Les options sur actions americaines peuvent etre exercees avant l'echeance, ce que Black-Scholes ignore.")

    with st.expander("tableau"):
        st.dataframe(res.style.format({"bid": "{:.2f}", "ask": "{:.2f}", "mid": "{:.2f}", "iv": "{:.2%}", "iv_yahoo": "{:.2%}"}), width="stretch")
