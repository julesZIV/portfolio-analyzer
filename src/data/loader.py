import yfinance as yf
import pandas as pd
import glob
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dataset")


def data_path(ticker, start, end, interval, dir=DIR):
    return os.path.join(dir, f"{ticker}_{start}_{end}_{interval}_data.csv")


def load_data(ticker, start, end, interval, dir=DIR):
    path = data_path(ticker, start, end, interval, dir)
    os.makedirs(dir, exist_ok=True)

    if not os.path.exists(path):
        res = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
        if res is None or res.empty:
            raise ValueError(f"No data found for {ticker} between {start} and {end}.")
        if isinstance(res.columns, pd.MultiIndex):
            res.columns = res.columns.droplevel("Ticker")
        res.index.name = "Date"
        res.to_csv(path)
    else:
        res = pd.read_csv(path, index_col="Date", parse_dates=True)
    return res


def delete_file(ticker, start, end, interval, dir=DIR):
    path = data_path(ticker, start, end, interval, dir)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def delete_dir_files(dir=DIR):
    if not os.path.exists(dir):
        return False
    for f in glob.glob(os.path.join(dir, "*.csv")):
        if os.path.isfile(f):
            os.remove(f)
    return True


def _close_column(res, tickers):
    if isinstance(res.columns, pd.MultiIndex):
        prices = res["Close"]
    else:
        prices = res[["Close"]].rename(columns={"Close": tickers[0]})
    return prices.dropna(axis=1, how="all")


def market_prices(tickers, start, end=None, complete=True):
    res = yf.download(list(tickers), start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    if res is None or res.empty:
        raise ValueError("No market data received.")
    prices = _close_column(res, list(tickers)).ffill()
    prices = prices.dropna() if complete else prices.dropna(how="all")
    prices.index.name = "Date"
    return prices


def market_ohlc(ticker, start, end=None):
    res = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    if res is None or res.empty:
        raise ValueError(f"No market data received for {ticker}.")
    if isinstance(res.columns, pd.MultiIndex):
        res.columns = res.columns.droplevel("Ticker")
    res = res[["Open", "High", "Low", "Close"]].dropna()
    res.index.name = "Date"
    return res


def latest_quotes(tickers):
    res = yf.download(list(tickers), period="7d", interval="1d", auto_adjust=True, progress=False)
    if res is None or res.empty:
        raise ValueError("No quotes received.")
    prices = _close_column(res, list(tickers))
    rows = {}
    for t in prices.columns:
        series = prices[t].dropna()
        if len(series) >= 2:
            rows[t] = {"last": series.iloc[-1], "previous": series.iloc[-2],
                       "change": series.iloc[-1] / series.iloc[-2] - 1, "date": series.index[-1]}
    return pd.DataFrame.from_dict(rows, orient="index")


if __name__ == "__main__":
    data = load_data("AC.PA", "2018-01-04", "2018-12-30", "1d")
    print(data)
