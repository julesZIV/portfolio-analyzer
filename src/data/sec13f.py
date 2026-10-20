import json
import os
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "portfolio-analyzer personal-project admin@portfolio-analyzer.local")
OPENFIGI_API_KEY = os.environ.get("OPENFIGI_API_KEY")
TICKER_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dataset", "cusip_tickers.json")

INVESTORS = {
    "Warren Buffett":{"fund": "Berkshire Hathaway", "cik": 1067983},
    "Bill Ackman":{"fund": "Pershing Square","cik": 1336528},
    "Cathie Wood":{"fund": "ARK Investment Management","cik": 1697748},
    "Stanley Druckenmiller":{"fund": "Duquesne Family Office","cik": 1536411},
    "David Tepper":{"fund": "Appaloosa","cik": 1656456},
    "Seth Klarman": {"fund": "Baupost Group","cik": 1061768},
    "Li Lu": {"fund": "Himalaya Capital","cik": 1709323},
    "George Soros":{"fund": "Soros Fund Management","cik": 1029160},
    "Ray Dalio":{"fund": "Bridgewater Associates","cik": 1350694},
    "Bill Gates":{"fund": "Gates Foundation Trust","cik": 1166559},
    "Michael Burry": {"fund": "Scion Asset Management","cik": 1649339},
}


def _get(url):
    r = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)
    r.raise_for_status()
    time.sleep(0.12)
    return r


def list_filings(cik):
    recent = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()["filings"]["recent"]
    df = pd.DataFrame({
        "form": recent["form"],
        "accession": recent["accessionNumber"],
        "filing_date": pd.to_datetime(recent["filingDate"]),
        "report_date": pd.to_datetime(recent["reportDate"]),
    })
    df = df[df["form"] == "13F-HR"].sort_values("report_date", ascending=False)
    return df.drop_duplicates("report_date").reset_index(drop=True)


def filing_holdings(cik, accession):
    folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}"
    files = [f["name"] for f in _get(f"{folder}/index.json").json()["directory"]["item"]]
    candidates = [f for f in files if f.lower().endswith(".xml") and f != "primary_doc.xml"]
    for file in candidates:
        root = ET.fromstring(_get(f"{folder}/{file}").content)
        ns = {"n": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {"n": ""}
        rows = root.findall("n:infoTable", ns)
        if rows:
            break
    else:
        raise ValueError("13F information table not found in the filing.")

    def field(row, path):
        node = row.find(path, ns)
        return node.text.strip() if node is not None and node.text else ""

    df = pd.DataFrame([{
        "issuer": field(r, "n:nameOfIssuer"),
        "cusip": field(r, "n:cusip").upper(),
        "value": float(field(r, "n:value") or 0),
        "shares": float(field(r, "n:shrsOrPrnAmt/n:sshPrnamt") or 0),
        "option": field(r, "n:putCall"),
    } for r in rows])
    return (df.groupby(["cusip", "option"], as_index=False)
              .agg(issuer=("issuer", "first"), value=("value", "sum"), shares=("shares", "sum"))
              .sort_values("value", ascending=False, ignore_index=True))


def _read_cache():
    try:
        with open(TICKER_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _openfigi(cusips, id_type="ID_CUSIP"):
    headers = {"Content-Type": "application/json"}
    if OPENFIGI_API_KEY:
        headers["X-OPENFIGI-APIKEY"] = OPENFIGI_API_KEY
    query = [{"idType": id_type, "idValue": c} for c in cusips]
    for attempt in range(4):
        r = requests.post("https://api.openfigi.com/v3/mapping", headers=headers, json=query, timeout=30)
        if r.status_code != 429:
            break
        time.sleep(6 * (attempt + 1))
    r.raise_for_status()
    if not OPENFIGI_API_KEY:
        time.sleep(2.5)
    result = {}
    for c, res in zip(cusips, r.json()):
        data = res.get("data") or []
        match = next((d for d in data if d.get("exchCode") == "US"), None)
        result[c] = match["ticker"].replace("/", "-") if match else None
    return result


def cusip_to_ticker(cusips):
    cache = _read_cache()
    missing = [c for c in dict.fromkeys(cusips) if c not in cache]
    batch_size = 100 if OPENFIGI_API_KEY else 10
    try:
        for i in range(0, len(missing), batch_size):
            batch = missing[i:i + batch_size]
            found = _openfigi(batch)
            not_found = [c for c, t in found.items() if not t]
            if not_found:
                found |= _openfigi(not_found, "ID_CINS")
            cache |= found
    except requests.RequestException:
        pass
    os.makedirs(os.path.dirname(TICKER_CACHE), exist_ok=True)
    with open(TICKER_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=0, sort_keys=True)
    return {c: cache.get(c) for c in cusips}


def compare(current, previous):
    a = current.set_index("cusip")
    p = previous.set_index("cusip")
    df = pd.DataFrame({
        "issuer": a["issuer"].combine_first(p["issuer"]),
        "shares": a["shares"], "shares_before": p["shares"],
        "weight": a["value"] / a["value"].sum(), "weight_before": p["value"] / p["value"].sum(),
    }).fillna({"shares": 0, "shares_before": 0, "weight": 0, "weight_before": 0})
    df["shares_change"] = df["shares"] / df["shares_before"].where(df["shares_before"] > 0) - 1
    df["weight_change"] = df["weight"] - df["weight_before"]
    df["action"] = "Unchanged"
    df.loc[df["shares_change"] > 0.01, "action"] = "Added"
    df.loc[df["shares_change"] < -0.01, "action"] = "Reduced"
    df.loc[df["shares_before"] == 0, "action"] = "New"
    df.loc[df["shares"] == 0, "action"] = "Sold"
    return df.sort_values("weight_change", key=abs, ascending=False)
