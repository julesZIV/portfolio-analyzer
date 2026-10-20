import pandas as pd
import glob
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dataset")


def price_frame(dir=DIR):
    files = glob.glob(os.path.join(dir, "*.csv"))
    prices = pd.concat([pd.read_csv(f, index_col="Date", parse_dates=True)["Close"] for f in files], axis=1)
    prices.columns = [os.path.basename(f).split("_")[0] for f in files]
    return prices


def daily_returns(prices):
    return prices.pct_change().dropna()


def annual_return(prices):
    return (1 + daily_returns(prices).mean()) ** 252 - 1
