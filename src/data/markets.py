MARKETS = {
    "^GSPC": {"name": "S&P 500", "category": "US stocks", "unit": "pts"},
    "^NDX": {"name": "Nasdaq 100", "category": "US stocks", "unit": "pts"},
    "^DJI": {"name": "Dow Jones", "category": "US stocks", "unit": "pts"},
    "^RUT": {"name": "Russell 2000", "category": "US stocks", "unit": "pts"},
    "^FCHI": {"name": "CAC 40", "category": "Europe stocks", "unit": "pts"},
    "^GDAXI": {"name": "DAX", "category": "Europe stocks", "unit": "pts"},
    "^STOXX50E": {"name": "Euro Stoxx 50", "category": "Europe stocks", "unit": "pts"},
    "^FTSE": {"name": "FTSE 100", "category": "Europe stocks", "unit": "pts"},
    "^N225": {"name": "Nikkei 225", "category": "Asia stocks", "unit": "pts"},
    "^HSI": {"name": "Hang Seng", "category": "Asia stocks", "unit": "pts"},
    "000001.SS": {"name": "Shanghai Composite", "category": "Asia stocks", "unit": "pts"},
    "^BSESN": {"name": "Sensex", "category": "Asia stocks", "unit": "pts"},
    "GC=F": {"name": "Gold", "category": "Commodities", "unit": "$/oz"},
    "SI=F": {"name": "Silver", "category": "Commodities", "unit": "$/oz"},
    "BZ=F": {"name": "Brent oil", "category": "Commodities", "unit": "$/bbl"},
    "CL=F": {"name": "WTI oil", "category": "Commodities", "unit": "$/bbl"},
    "BTC-USD": {"name": "Bitcoin", "category": "Crypto", "unit": "$"},
    "ETH-USD": {"name": "Ethereum", "category": "Crypto", "unit": "$"},
    "EURUSD=X": {"name": "EUR/USD", "category": "FX and rates", "unit": ""},
    "USDJPY=X": {"name": "USD/JPY", "category": "FX and rates", "unit": ""},
    "^TNX": {"name": "US 10Y yield", "category": "FX and rates", "unit": "%"},
    "^VIX": {"name": "VIX", "category": "FX and rates", "unit": "pts"},
}
MARKET_TICKERS = list(MARKETS.keys())
HEADLINE_TICKERS = ["^GSPC", "^NDX", "^FCHI", "^GDAXI", "^N225", "GC=F", "BZ=F", "BTC-USD"]
SP500 = "^GSPC"
