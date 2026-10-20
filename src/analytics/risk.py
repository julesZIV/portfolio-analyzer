from analytics.returns import daily_returns
import numpy as np


def volatility(prices):
    return daily_returns(prices).std() * np.sqrt(252)


def covariance(prices):
    return daily_returns(prices).cov() * 252


def drawdown(prices):
    return prices / prices.cummax() - 1


def max_drawdown(prices):
    return drawdown(prices).min()


def sharpe_ratio(prices, risk_free_rate=0.0):
    returns = daily_returns(prices)
    excess_return = returns.mean() - risk_free_rate / 252
    return (excess_return / returns.std()) * np.sqrt(252)


def sortino_ratio(prices, risk_free_rate=0.0):
    returns = daily_returns(prices)
    downside_risk = np.sqrt((returns.clip(upper=0) ** 2).mean())
    excess_return = returns.mean() - risk_free_rate / 252
    return (excess_return / downside_risk) * np.sqrt(252)

def alpha(prices, benchmark_prices, risk_free_rate=0.0):
    returns = daily_returns(prices)
    benchmark_returns = benchmark_prices.pct_change().reindex(returns.index)
    beta_value = returns.apply(lambda r: r.cov(benchmark_returns) / benchmark_returns.var())
    excess_return = returns.mean() - risk_free_rate / 252
    benchmark_excess_return = benchmark_returns.mean() - risk_free_rate / 252
    return excess_return - beta_value * benchmark_excess_return


def beta(prices, benchmark_prices):
    returns = daily_returns(prices)
    benchmark_returns = benchmark_prices.pct_change().reindex(returns.index)
    return returns.apply(lambda r: r.cov(benchmark_returns) / benchmark_returns.var())
