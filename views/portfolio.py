from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from data.universe import CAC40, BENCHMARK
from data.loader import market_prices, latest_quotes
from analytics.returns import daily_returns, annual_return
from analytics.risk import volatility, covariance, drawdown, max_drawdown, sharpe_ratio, sortino_ratio, beta
from analytics.optimization import monte_carlo, min_variance, max_sharpe, efficient_frontier, portfolio_performance
from viz import charts
from viz.ui import REFRESH, assign_colors
from views.profil import afficher_profil

NAMES = {t: v["name"] for t, v in CAC40.items()} | {BENCHMARK: "CAC 40"}
PERIODS = {"1W":7,"1M": 30, "3M": 90, "6M": 182, "1Y": 365, "2Y": 730, "5Y": 1826}
RISK_FREE = 0.02


@st.cache_data(ttl=3600)
def history(tickers, start):
    return market_prices(list(tickers) + [BENCHMARK], start)


@st.cache_data(ttl=55)
def quotes(tickers):
    return latest_quotes(list(tickers) + [BENCHMARK])


@st.cache_data(ttl=3600)
def optimize(prices, rf):
    ret = annual_return(prices).values
    cov = covariance(prices).values
    return (monte_carlo(ret, cov, rf, n_sim=3000), efficient_frontier(ret, cov, n_points=40),max_sharpe(ret, cov, rf), min_variance(ret, cov), ret, cov)


st.title("portfolio cac 40")
st.write("choisir des actions et une periode")
afficher_profil()
tickers = st.multiselect("actions", list(CAC40), default=["MC.PA", "TTE.PA", "AIR.PA", "SAN.PA", "BNP.PA"],format_func=lambda t: CAC40[t]["name"], max_selections=8)
period = st.selectbox("periode", list(PERIODS), index=2)

if len(tickers) < 2:
    st.write("il faut au moins 2 actions")
    st.stop()

colors = assign_colors(tickers, "colors_portfolio")

try:
    all_prices = history(tuple(tickers), (date.today() - timedelta(days=PERIODS[period])).isoformat())
except Exception as e:
    st.write("erreur :", e)
    st.stop()

tickers = [t for t in tickers if t in all_prices.columns]
prices = all_prices[tickers]
bench = all_prices[BENCHMARK] if BENCHMARK in all_prices else None


# prix en direct
@st.fragment(run_every=REFRESH)
def live():
    st.write("### prix live")
    try:
        q = quotes(tuple(tickers))
    except Exception as e:
        st.write("pas de prix", e)
        return
    st.write("maj", datetime.now().strftime("%H:%M:%S"))
    cols = st.columns(len(q))
    for i, t in enumerate(q.index):
        cols[i].metric(NAMES.get(t, t), round(q.loc[t, "last"], 2), f"{q.loc[t, 'change']:.2%}")

live()

stats = pd.DataFrame({
    "return": annual_return(prices),
    "vol": volatility(prices),
    "sharpe": sharpe_ratio(prices, RISK_FREE),
    "sortino": sortino_ratio(prices, RISK_FREE),
    "maxdd": max_drawdown(prices),
    "beta": beta(prices, bench) if bench is not None else np.nan,
})

bench_stats = None
if bench is not None:
    bench_stats = {"return": annual_return(bench.to_frame()).iloc[0], "volatility": volatility(bench.to_frame()).iloc[0]}

# perf
st.write("### performance")
st.write("base 100 au debut de la periode, la ligne grise c'est le cac 40")
st.plotly_chart(charts.base_100(prices, colors, NAMES, bench, "CAC 40"))
perf = prices.iloc[-1] / prices.iloc[0] - 1
st.write("perf sur la periode :")
st.write(perf.rename(index=NAMES))

# risque
st.write("### risque")
st.write("rendement vs volatilité (en haut a gauche = mieux)")
st.plotly_chart(charts.risk_return(stats.rename(columns={"vol": "volatility"}), colors, NAMES, bench_stats, "CAC 40"))
st.write("drawdown = combien ca a baissé depuis le plus haut")
st.plotly_chart(charts.drawdowns(drawdown(prices), colors, NAMES, drawdown(bench) if bench is not None else None, "CAC 40"))
st.write("tableau des stats")
st.dataframe(stats.rename(index=NAMES))

# correl
st.write("### correlation")
st.write("rouge = bougent pareil, bleu = inverse")
st.plotly_chart(charts.correlations(daily_returns(prices), NAMES))

# markowitz
st.write("### optimisation (markowitz)")
try:
    cloud, front, w_sharpe, w_minvar, ret, cov = optimize(prices, RISK_FREE)
except Exception as e:
    st.write("optim a planté", e)
else:
    r_s, v_s = portfolio_performance(w_sharpe, ret, cov)
    r_m, v_m = portfolio_performance(w_minvar, ret, cov)
    st.write("points gris = portefeuilles random, ligne bleue = frontiere efficiente")
    st.plotly_chart(charts.frontier(cloud, front, stats[["return", "vol"]].rename(columns={"vol": "volatility"}),colors, NAMES, (v_s, r_s), (v_m, r_m)))
    st.write("max sharpe : rendement", round(r_s, 3), "vol", round(v_s, 3))
    st.write("min variance : rendement", round(r_m, 3), "vol", round(v_m, 3))
    weights = pd.DataFrame({"max sharpe": w_sharpe, "min var": w_minvar}, index=prices.columns)
    st.write("poids :")
    st.plotly_chart(charts.weights(weights, NAMES))
    st.write(weights.rename(index=NAMES))

st.write("donnees yahoo finance, pas un conseil")
