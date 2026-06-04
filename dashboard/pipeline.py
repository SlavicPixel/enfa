"""
Live data refresh pipeline.
Fetches latest prices + news, recomputes features, updates MongoDB.
Called by RefreshDataView and the scheduler.
"""

import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError

TICKERS = ["NVDA", "AMD", "MSFT", "TSM", "AVGO", "META", "GOOGL", "AMZN", "INTC"]
MOVE_THRESHOLD  = 0.03
AFTER_HOURS_UTC = 20

TICKER_QUERIES = {
    "NVDA":  "Nvidia",
    "AMD":   "AMD semiconductor",
    "MSFT":  "Microsoft AI",
    "TSM":   "TSMC chips",
    "AVGO":  "Broadcom AI",
    "META":  "Meta AI",
    "GOOGL": "Google Gemini AI",
    "AMZN":  "Amazon AWS AI",
    "INTC":  "Intel semiconductor",
}
GENERAL_QUERIES = [
    "artificial intelligence stocks",
    "AI chips semiconductor",
    "ChatGPT market",
]


def get_db():
    from django.conf import settings
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB]


# ── Prices ────────────────────────────────────────────────────────────────

def refresh_prices(db):
    col = db["stock_prices"]
    col.create_index([("ticker", ASCENDING), ("date", ASCENDING)], unique=True)

    total = 0
    for ticker in TICKERS:
        # Find last stored date for this ticker
        last = col.find_one({"ticker": ticker}, sort=[("date", -1)])
        start = (
            datetime.strptime(last["date"], "%Y-%m-%d") + timedelta(days=1)
            if last else datetime(2022, 1, 1)
        )
        end = datetime.today()
        if start.date() >= end.date():
            continue

        df = yf.download(ticker,
                         start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"),
                         progress=False)
        if df.empty:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        docs = [{
            "ticker": ticker,
            "date":   str(row["date"])[:10],
            "open":   float(row["open"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": int(row["volume"]),
        } for _, row in df.iterrows()]

        if docs:
            try:
                col.insert_many(docs, ordered=False)
                total += len(docs)
            except BulkWriteError as e:
                total += e.details.get("nInserted", 0)

    print(f"  Prices: {total} new rows")


# ── News ──────────────────────────────────────────────────────────────────

def refresh_news(db):
    from django.conf import settings as django_settings
    api_key = os.environ.get("NEWSAPI_KEY") or getattr(django_settings, "NEWSAPI_KEY", None)
    if not api_key or api_key == "your_api_key_here":
        print("  News: NEWSAPI_KEY not set, skipping")
        return

    col = db["news_articles"]
    col.create_index([("url", ASCENDING)], unique=True, sparse=True)

    to_date   = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=29)).strftime("%Y-%m-%d")
    total     = 0

    all_queries = list(TICKER_QUERIES.items()) + [(None, q) for q in GENERAL_QUERIES]

    for ticker, query in all_queries:
        try:
            resp = requests.get("https://newsapi.org/v2/everything", params={
                "q":        query,
                "from":     from_date,
                "to":       to_date,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": 100,
                "apiKey":   api_key,
            }, timeout=10)
            data = resp.json()
            status   = data.get("status")
            n_total  = data.get("totalResults", 0)
            articles = data.get("articles") or []
            print(f"  [{ticker or 'general'}] status={status} total={n_total} returned={len(articles)}")
            if status != "ok":
                print(f"    API message: {data.get('message')}")
                continue

            docs = []
            for a in data.get("articles") or []:
                if not a.get("url") or a.get("title") == "[Removed]":
                    continue
                docs.append({
                    "ticker":       ticker,
                    "query":        query,
                    "title":        (a.get("title") or "")[:500],
                    "description":  (a.get("description") or "")[:1000],
                    "source":       (a.get("source") or {}).get("name"),
                    "published_at": a.get("publishedAt", ""),
                    "url":          (a.get("url") or "")[:500],
                    "fetched_at":   datetime.now().isoformat(),
                    "language":     "en",
                })

            if docs:
                try:
                    col.insert_many(docs, ordered=False)
                    total += len(docs)
                except BulkWriteError as e:
                    total += e.details.get("nInserted", 0)

        except Exception as e:
            print(f"  News error ({query}): {e}")

    print(f"  News: {total} new articles")


# ── Features ──────────────────────────────────────────────────────────────

def compute_indicators(df):
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    ret = c.pct_change()

    df["sma_20_ratio"]      = c / c.rolling(20).mean()
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi_14"]            = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]              = ema12 - ema26
    df["macd_signal"]       = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]         = df["macd"] - df["macd_signal"]
    sma20 = c.rolling(20).mean(); std20 = c.rolling(20).std()
    df["bb_pos"]            = (c - (sma20 - 2*std20)) / (4 * std20.replace(0, np.nan))
    tp  = (h + l + c) / 3
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["cci_20"]            = (tp - tp.rolling(20).mean()) / (0.015 * mad.replace(0, np.nan))
    up  = h.diff(); dn = -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr  = pd.concat([(h-l),(h-c.shift()).abs(),(l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).rolling(14).mean() / atr
    mdi = 100 * pd.Series(mdm, index=df.index).rolling(14).mean() / atr
    dx  = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    df["adx_14"]            = dx.rolling(14).mean()
    df["daily_return"]      = ret
    df["volume_change"]     = v.pct_change()
    df["realized_vol_5"]    = ret.rolling(5).std()
    df["realized_vol_10"]   = ret.rolling(10).std()
    df["hl_range"]          = (h - l) / c
    df["hl_range_5"]        = df["hl_range"].rolling(5).mean()
    prev_c = c.shift(1)
    tr2 = pd.concat([(h-l),(h-prev_c).abs(),(l-prev_c).abs()], axis=1).max(axis=1)
    df["atr_norm_14"]       = tr2.rolling(14).mean() / c
    df["large_move_count_5"]= (ret.abs() >= MOVE_THRESHOLD).rolling(5).sum()
    df["volume_ratio"]      = v / v.rolling(20).mean()
    return df


def refresh_features(db):
    col_px   = db["stock_prices"]
    col_feat = db["training_features"]
    col_feat.create_index([("ticker", ASCENDING), ("date", ASCENDING)], unique=True)
    col_news = db["news_articles"]

    total = 0
    for ticker in TICKERS:
        # Load all prices for this ticker (need full history for rolling windows)
        px_docs = list(col_px.find({"ticker": ticker}, {"_id": 0},
                                    sort=[("date", 1)]))
        if len(px_docs) < 60:
            continue

        px = pd.DataFrame(px_docs)
        px["date"] = pd.to_datetime(px["date"])
        px = compute_indicators(px)

        # Aggregate sentiment per trading day
        news_docs = list(col_news.find(
            {"ticker": ticker, "sentiment": {"$ne": None}},
            {"_id": 0, "published_at": 1, "sentiment": 1,
             "sentiment_positive": 1, "sentiment_negative": 1,
             "sentiment_neutral": 1}
        ))
        sent_rows = []
        for n in news_docs:
            ts = pd.to_datetime(n["published_at"], utc=True, errors="coerce")
            if pd.isna(ts):
                continue
            eff = ts.normalize()
            if ts.hour >= AFTER_HOURS_UTC:
                eff += timedelta(days=1)
            sent_rows.append({
                "eff_date":          eff.date(),
                "sentiment_positive": n.get("sentiment_positive", 0) or 0,
                "sentiment_negative": n.get("sentiment_negative", 0) or 0,
                "sentiment_neutral":  n.get("sentiment_neutral", 0) or 0,
                "is_pos": 1 if n.get("sentiment") == "positive" else 0,
                "is_neg": 1 if n.get("sentiment") == "negative" else 0,
            })

        trading_days = sorted(px["date"].dt.date.tolist())
        td_arr = np.array(trading_days)

        if sent_rows:
            sdf = pd.DataFrame(sent_rows)
            grp = sdf.groupby("eff_date").agg(
                avg_pos=("sentiment_positive", "mean"),
                avg_neg=("sentiment_negative", "mean"),
                avg_neu=("sentiment_neutral",  "mean"),
                article_count=("is_pos", "size"),
                pos_ratio=("is_pos", "mean"),
                neg_ratio=("is_neg", "mean"),
            ).reset_index()
            grp["net_sentiment"] = grp["avg_pos"] - grp["avg_neg"]

            # Map each eff_date to next trading day
            grp["trading_day"] = grp["eff_date"].apply(
                lambda d: td_arr[np.searchsorted(td_arr, d)]
                if np.searchsorted(td_arr, d) < len(td_arr) else None
            )
            grp = grp.dropna(subset=["trading_day"])
            grp = grp.groupby("trading_day").agg({
                "avg_pos": "mean", "avg_neg": "mean", "avg_neu": "mean",
                "article_count": "sum", "pos_ratio": "mean",
                "neg_ratio": "mean", "net_sentiment": "mean",
            }).reset_index().rename(columns={"trading_day": "date_key"})
            sent_map = {row["date_key"]: row for _, row in grp.iterrows()}
        else:
            sent_map = {}

        # Build feature rows
        px = px.sort_values("date").reset_index(drop=True)
        px["net_sentiment"]    = px["date"].dt.date.map(
            lambda d: sent_map.get(d, {}).get("net_sentiment", 0))
        px["net_sentiment_3d"] = px["net_sentiment"].rolling(3, min_periods=1).mean()
        px["net_sentiment_5d"] = px["net_sentiment"].rolling(5, min_periods=1).mean()

        feature_cols = [
            "sma_20_ratio","rsi_14","macd","macd_signal","macd_hist",
            "bb_pos","cci_20","adx_14","daily_return","volume_change",
            "realized_vol_5","realized_vol_10","hl_range","hl_range_5",
            "atr_norm_14","large_move_count_5","volume_ratio",
            "net_sentiment","net_sentiment_3d","net_sentiment_5d",
        ]
        px = px.dropna(subset=feature_cols)

        docs = []
        for _, row in px.iterrows():
            d    = row["date"].date()
            sent = sent_map.get(d, {})
            doc  = {
                "ticker": ticker,
                "date":   str(d),
                "has_news":      1 if d in sent_map else 0,
                "avg_pos":       sent.get("avg_pos", 0),
                "avg_neg":       sent.get("avg_neg", 0),
                "avg_neu":       sent.get("avg_neu", 0),
                "article_count": sent.get("article_count", 0),
                "pos_ratio":     sent.get("pos_ratio", 0),
                "neg_ratio":     sent.get("neg_ratio", 0),
            }
            for col in feature_cols:
                doc[col] = float(row[col]) if pd.notna(row[col]) else 0.0
            docs.append(doc)

        if docs:
            try:
                col_feat.insert_many(docs, ordered=False)
                total += len(docs)
            except BulkWriteError as e:
                total += e.details.get("nInserted", 0)

    print(f"  Features: {total} new rows")


# ── Entry point ───────────────────────────────────────────────────────────

def run_refresh():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting refresh...")
    db = get_db()
    refresh_prices(db)
    refresh_news(db)
    refresh_features(db)
    print("Refresh complete.")