import pandas as pd
from analytics.black_scholes import delta, gamma, vega, theta, rho

def greeks(S, K, T, r, sigma, option_type="call", q=0.0):
    # S : prix du sous-jacent
    # K : prix d'exercice
    # T : maturité en années
    # r : taux sans risque
    # sigma : volatilité implicite
    # option_type : "call" ou "put"
    # q : taux de dividende
    return pd.Series({
        "delta": delta(S, K, T, r, sigma, option_type, q),
        "gamma": gamma(S, K, T, r, sigma, option_type, q),
        "vega": vega(S, K, T, r, sigma, q),
        "theta": theta(S, K, T, r, sigma, option_type, q),
        "rho": rho(S, K, T, r, sigma, option_type, q),
    })
