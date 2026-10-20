import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

# q = taux de dividende continu (0 par defaut = Black-Scholes classique, sinon modele de Merton)

def _d1_d2(S, K, T, r, sigma, q=0.0):
    d1=(np.log(S/K)+(r-q+sigma**2*0.5)*T)/(sigma*np.sqrt(T))
    d2=d1-sigma*np.sqrt(T)
    return d1, d2

def black_scholes_price(S, K, T, r, sigma, option_type="call", q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)

    if option_type=="call":
        C=S*np.exp(-q*T)*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2)

    elif option_type=="put":
        C=K*np.exp(-r*T)*norm.cdf(-d2)-S*np.exp(-q*T)*norm.cdf(-d1)

    else:
        raise ValueError(f"option_type inconnu : {option_type}")

    return C

def vega(S, K, T, r, sigma, q=0.0):
    #vega = cours actuel actualise du dividende * densite de la loi N CR en d1 * racine du temps restant
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return S*np.exp(-q*T)*norm.pdf(d1)*np.sqrt(T) #par point

def parity_price(S, K, T, r, option_type="call", q=0.0):
    #parite call-put : renvoie C - P pour "call" et P - C pour "put" (pas le prix d'une option seule)
    if option_type=="call":
        C=S*np.exp(-q*T)-K*np.exp(-r*T)
    elif option_type=="put":
        C=K*np.exp(-r*T)-S*np.exp(-q*T)
    else:
        raise ValueError(f"option_type inconnu : {option_type}")
    return C

def implied_volatility(S, K, T, r, market_price, option_type="call", q=0.0):
    def objective_function(sigma):
        return black_scholes_price(S, K, T, r, sigma, option_type, q) - market_price
    try:
        implied_vol = brentq(objective_function, 1e-6, 5) #recherche de la racine de f sur l'intervalle [1e-6, 5] soit une vol entre 0 et 500%
    except ValueError:
        implied_vol = np.nan

    return implied_vol

def Newton_Raphson(S, K, T, r, market_price, option_type="call", tol=1e-6, max_iter=100, q=0.0):
    sigma = approx_initial_vol(S, T, market_price, option_type)
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = 0.2
    sigma = min(max(sigma, 0.01), 5)
    for i in range(max_iter):
        price = black_scholes_price(S, K, T, r, sigma, option_type, q)
        price_diff = price - market_price
        if abs(price_diff) < tol:
            return sigma
        v = vega(S, K, T, r, sigma, q)
        if v < 1e-8: #vega quasi nul (option tres dans/hors la monnaie) : Newton diverge, on bascule sur brentq
            return implied_volatility(S, K, T, r, market_price, option_type, q)
        sigma -= price_diff / v
        if sigma <= 0 or sigma > 5: #sortie de l'intervalle raisonnable : on bascule sur brentq
            return implied_volatility(S, K, T, r, market_price, option_type, q)
    return np.nan #pas de convergence

def approx_initial_vol(S, T, market_price, option_type="call"):
    #approximation de Brenner-Subrahmanyam (valable pres de la monnaie) : sigma ~= sqrt(2*pi/T) * prix / S
    #s'applique au call comme au put car a la monnaie C ~= P
    return np.sqrt(2*np.pi/T)*market_price/S

def borne_arbitrage(S, K, T, r, market_price, option_type="call", q=0.0):
    if option_type=="call":
        lower_bound = max(0, S*np.exp(-q*T) - K*np.exp(-r*T))
        upper_bound = S*np.exp(-q*T)
    elif option_type=="put":
        lower_bound = max(0, K*np.exp(-r*T) - S*np.exp(-q*T))
        upper_bound = K*np.exp(-r*T)
    else:
        raise ValueError(f"option_type inconnu : {option_type}")
    return lower_bound, upper_bound

def rho(S, K, T, r, sigma, option_type="call", q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    if option_type=="call":
        return K*T*np.exp(-r*T)*norm.cdf(d2)   #par point de taux
    elif option_type=="put":
        return -K*T*np.exp(-r*T)*norm.cdf(-d2)#par point de taux
    else:
        raise ValueError(f"option_type inconnu : {option_type}")

def gamma(S, K, T, r, sigma, option_type="call", q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return np.exp(-q*T)*norm.pdf(d1)/(S*sigma*np.sqrt(T))

def delta(S, K, T, r, sigma, option_type="call", q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    if option_type=="call":
        return np.exp(-q*T)*norm.cdf(d1)
    elif option_type=="put":
        return np.exp(-q*T)*(norm.cdf(d1)-1)
    else:
        raise ValueError(f"option_type inconnu : {option_type}")

def theta(S, K, T, r, sigma, option_type="call", q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    if option_type=="call":
        return (-S*np.exp(-q*T)*norm.pdf(d1)*sigma/(2*np.sqrt(T)) - r*K*np.exp(-r*T)*norm.cdf(d2) + q*S*np.exp(-q*T)*norm.cdf(d1))  #par jour
    elif option_type=="put":
        return (-S*np.exp(-q*T)*norm.pdf(d1)*sigma/(2*np.sqrt(T)) + r*K*np.exp(-r*T)*norm.cdf(-d2) - q*S*np.exp(-q*T)*norm.cdf(-d1))#par jour
    else:
        raise ValueError(f"option_type inconnu : {option_type}")  