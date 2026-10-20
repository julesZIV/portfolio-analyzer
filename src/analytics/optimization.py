import numpy as np
import pandas as pd
from scipy.optimize import minimize


def sum_to_one_constraint():
    return ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)


def weight_bounds(n):
    return tuple((0, 1) for _ in range(n))


def portfolio_performance(weights, annual_returns, annual_cov):
    ret = weights @ annual_returns
    vol = np.sqrt(weights @ annual_cov @ weights)
    return ret, vol


def portfolio_sharpe(weights, annual_returns, annual_cov, rf):
    ret, vol = portfolio_performance(weights, annual_returns, annual_cov)
    return (ret - rf) / vol


def monte_carlo(annual_returns, annual_cov, rf, n_sim=10000):
    n = len(annual_returns)
    results = []
    for _ in range(n_sim):
        weights = np.random.random(n)
        weights /= weights.sum()
        ret, vol = portfolio_performance(weights, annual_returns, annual_cov)
        results.append({"return": ret, "volatility": vol, "sharpe": (ret - rf) / vol, "weights": weights})
    return pd.DataFrame(results)


def min_variance(annual_returns, annual_cov):
    n = len(annual_returns)
    result = minimize(
        lambda w: portfolio_performance(w, annual_returns, annual_cov)[1],
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=weight_bounds(n),
        constraints=sum_to_one_constraint(),
    )
    if not result.success:
        raise RuntimeError(f"Minimum variance optimization failed: {result.message}")
    return result.x


def max_sharpe(annual_returns, annual_cov, rf):
    n = len(annual_returns)
    result = minimize(
        lambda w: -portfolio_sharpe(w, annual_returns, annual_cov, rf),
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=weight_bounds(n),
        constraints=sum_to_one_constraint(),
    )
    if not result.success:
        raise RuntimeError(f"Maximum Sharpe optimization failed: {result.message}")
    return result.x


def efficient_portfolio(annual_returns, annual_cov, target_return):
    n = len(annual_returns)
    constraints = (
        {"type": "eq", "fun": lambda w: np.sum(w) - 1},
        {"type": "eq", "fun": lambda w: portfolio_performance(w, annual_returns, annual_cov)[0] - target_return},
    )
    result = minimize(
        lambda w: portfolio_performance(w, annual_returns, annual_cov)[1],
        np.repeat(1 / n, n),
        method="SLSQP",
        bounds=weight_bounds(n),
        constraints=constraints,
    )
    if not result.success:
        return None
    return result.x


def efficient_frontier(annual_returns, annual_cov, n_points=50):
    targets = np.linspace(annual_returns.min(), annual_returns.max(), n_points)
    points = []
    for target in targets:
        weights = efficient_portfolio(annual_returns, annual_cov, target)
        if weights is None:
            continue
        ret, vol = portfolio_performance(weights, annual_returns, annual_cov)
        points.append({"return": ret, "volatility": vol})
    return pd.DataFrame(points)
