import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from analytics.black_scholes import (black_scholes_price, implied_volatility, Newton_Raphson, parity_price,
                                     borne_arbitrage, delta, gamma, vega, theta, rho)
from analytics.greeks import greeks
from analytics.optimization import min_variance, max_sharpe, portfolio_performance

S = 100
K = 100
T = 1
r = 0.05
sigma = 0.2
q = 0


def test_prix_reference():
    #valeurs de reference (Hull) : call ~= 10.4506, put ~= 5.5735
    assert abs(black_scholes_price(S, K, T, r, sigma, "call", q) - 10.4506) < 1e-4
    assert abs(black_scholes_price(S, K, T, r, sigma, "put", q) - 5.5735) < 1e-4


def test_parite_call_put():
    for div in (0.0, 0.03):
        c = black_scholes_price(S, K, T, r, sigma, "call", div)
        p = black_scholes_price(S, K, T, r, sigma, "put", div)
        assert abs((c - p) - parity_price(S, K, T, r, "call", div)) < 1e-10


def test_vol_implicite():
    for typ in ("call", "put"):
        price = black_scholes_price(S, 110, T, r, 0.3, typ, 0.01)
        assert abs(implied_volatility(S, 110, T, r, price, typ, 0.01) - 0.3) < 1e-6
        assert abs(Newton_Raphson(S, 110, T, r, price, typ, q=0.01) - 0.3) < 1e-5


def test_bornes_arbitrage():
    lo, hi = borne_arbitrage(S, K, T, r, 0, "call", q)
    assert lo <= black_scholes_price(S, K, T, r, sigma, "call", q) <= hi


def test_greeks_differences_finies():
    h = 1e-4
    for typ in ("call", "put"):
        g = greeks(S, K, T, r, sigma, typ, 0.02)
        price = lambda **kw: black_scholes_price(kw.get("S", S), K, kw.get("T", T), kw.get("r", r),
                                                 kw.get("sigma", sigma), typ, 0.02)
        assert abs(g["delta"] - (price(S=S + h) - price(S=S - h)) / (2 * h)) < 1e-6
        assert abs(g["gamma"] - (price(S=S + h) - 2 * price() + price(S=S - h)) / h**2) < 1e-3
        assert abs(g["vega"] - (price(sigma=sigma + h) - price(sigma=sigma - h)) / (2 * h)) < 1e-5
        assert abs(g["rho"] - (price(r=r + h) - price(r=r - h)) / (2 * h)) < 1e-5
        assert abs(g["theta"] + (price(T=T + h) - price(T=T - h)) / (2 * h)) < 1e-5
        assert g["delta"] == delta(S, K, T, r, sigma, typ, 0.02)


def test_optimisation():
    ret = np.array([0.08, 0.12, 0.05])
    cov = np.array([[0.04, 0.01, 0.0], [0.01, 0.09, 0.0], [0.0, 0.0, 0.01]])
    w_min = min_variance(ret, cov)
    w_sharpe = max_sharpe(ret, cov, 0.02)
    for w in (w_min, w_sharpe):
        assert abs(w.sum() - 1) < 1e-6 and (w >= -1e-8).all()
    assert portfolio_performance(w_min, ret, cov)[1] <= portfolio_performance(w_sharpe, ret, cov)[1] + 1e-8


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_") and callable(f):
            f()
            print("ok", name)
