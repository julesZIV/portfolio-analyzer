import numpy as np
from scipy.stats import norm
import pandas as pd
from analytics.black_scholes import _d1_d2, rho , delta, theta, black_scholes_price, vega, implied_volatility, borne_arbitrage

def greeks(S,o,r,T,sigma,K,option_type="call",q=0.0):
    # S : prix du sous-jacent
    # o : option (call ou put)
    # r : taux sans risque
    # T : maturité en années*
    # sigma : volatilité implicite
    # K : prix d'exercice
    # q : taux de dividende

    d1, _ = _d1_d2(S, K, T, r, sigma, q=q)
    delta = delta(S, K, T, r, sigma, option_type="call", q=q)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T)
    theta = theta(S, K, T, r, sigma, option_type="call", q=q)
    rho = rho(S, K, T, r, sigma, option_type="call", q=q)
    return pd.Series({"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho})

