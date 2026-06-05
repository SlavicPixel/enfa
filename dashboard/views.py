from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from enfa.mongo import get_db
from enfa.predictor import predict, get_bundle
from datetime import datetime, timedelta

TICKERS = ["NVDA", "AMD", "MSFT", "TSM", "AVGO", "META", "GOOGL", "AMZN", "INTC"]


# ── Helpers ───────────────────────────────────────────────────────────────

def get_latest_features(ticker: str) -> dict | None:
    db  = get_db()
    doc = db["training_features"].find_one(
        {"ticker": ticker},
        sort=[("date", -1)]
    )
    return doc


def get_price_history(ticker: str, days: int = 180) -> list:
    db    = get_db()
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    return list(db["stock_prices"].find(
        {"ticker": ticker, "date": {"$gte": since}},
        {"_id": 0, "date": 1, "close": 1, "volume": 1},
        sort=[("date", 1)]
    ))


def get_sentiment_history(ticker: str, days: int = 180) -> list:
    db    = get_db()
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    return list(db["training_features"].find(
        {"ticker": ticker, "date": {"$gte": since}},
        {"_id": 0, "date": 1, "net_sentiment": 1, "article_count": 1},
        sort=[("date", 1)]
    ))


def get_recent_news(ticker: str, limit: int = 15) -> list:
    db = get_db()
    return list(db["news_articles"].find(
        {"ticker": ticker, "sentiment": {"$ne": None}},
        {"_id": 0, "title": 1, "source": 1, "published_at": 1,
         "sentiment": 1, "url": 1},
        sort=[("published_at", -1)],
        limit=limit
    ))


# ── Views ─────────────────────────────────────────────────────────────────

class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        db  = get_db()
        overview = []
        for ticker in TICKERS:
            feat = get_latest_features(ticker)
            if not feat:
                continue
            result    = predict(ticker, feat)
            price_doc = db["stock_prices"].find_one(
                {"ticker": ticker}, sort=[("date", -1)])
            overview.append({
                "ticker":      ticker,
                "close":       round(price_doc["close"], 2) if price_doc else None,
                "date":        price_doc["date"] if price_doc else None,
                "volatile":    result["volatile"],
                "probability": result["probability"],
            })
        ctx["overview"] = overview
        return ctx


class TickerDetailView(LoginRequiredMixin, View):
    template_name = "dashboard/ticker.html"

    def get(self, request, ticker):
        ticker = ticker.upper()
        if ticker not in TICKERS:
            return render(request, "dashboard/404.html", status=404)

        feat   = get_latest_features(ticker)
        result = predict(ticker, feat) if feat else None
        bundle = get_bundle()

        # Top contributing features for this specific prediction
        explanation = []
        if feat and result:
            model     = bundle["model"]
            feat_cols = bundle["feature_columns"]
            coef      = model.coef_[0]
            scaler    = bundle["scaler"]

            import numpy as np
            row = {}
            for col in feat_cols:
                if col.startswith("tkr_"):
                    row[col] = 1.0 if col.replace("tkr_", "") == ticker else 0.0
                else:
                    row[col] = float(feat.get(col, 0) or 0)

            import pandas as pd
            X      = pd.DataFrame([row])[feat_cols].values
            X_sc   = scaler.transform(X)[0]
            contribs = X_sc * coef

            pairs = [
                {"feature": f, "contribution": round(float(c), 4)}
                for f, c in zip(feat_cols, contribs)
                if not f.startswith("tkr_")
            ]
            pairs.sort(key=lambda x: abs(x["contribution"]), reverse=True)
            top = pairs[:8]
            max_abs = max(abs(f["contribution"]) for f in top) if top else 1
            for f in top:
                f["width"] = round(abs(f["contribution"]) / max_abs * 100, 1)
            explanation = top

        ctx = {
            "ticker":      ticker,
            "result":      result,
            "explanation": explanation,
            "prices":      get_price_history(ticker, days=365),
            "sentiment":   get_sentiment_history(ticker, days=365),
            "news":        get_recent_news(ticker),
            "feat":        feat,
            "model_auc":   round(bundle.get("cv_auc_mean", 0) * 100, 1),
            "trained_at":  bundle.get("trained_at", ""),
        }
        return render(request, self.template_name, ctx)


class RefreshDataView(LoginRequiredMixin, View):
    """On-demand data refresh — fetches latest prices and news, updates MongoDB."""

    def post(self, request):
        try:
            from dashboard.pipeline import run_refresh
            run_refresh()
            return JsonResponse({"status": "ok",
                                 "message": "Data refreshed successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
        
class ModelInsightsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/model_insights.html"

    def get_context_data(self, **kwargs):
        ctx    = super().get_context_data(**kwargs)
        bundle = get_bundle()
        model  = bundle["model"]

        feat_cols    = bundle["feature_columns"]
        ticker_cols  = [c for c in feat_cols if c.startswith("tkr_")]
        feature_cols = [c for c in feat_cols if not c.startswith("tkr_")]

        # Feature importance from logistic regression coefficients
        # Use absolute mean coefficient across all features
        coef = model.coef_[0]
        importance = [
            {"feature": f, "coefficient": round(float(c), 4),
             "abs": round(abs(float(c)), 4)}
            for f, c in zip(feat_cols, coef)
            if not f.startswith("tkr_")
        ]
        importance.sort(key=lambda x: x["abs"], reverse=True)

        ctx.update({
            "bundle":       bundle,
            "model_auc":    round(bundle.get("cv_auc_mean", 0) * 100, 1),
            "model_std":    round(bundle.get("cv_auc_std", 0) * 100, 1),
            "trained_at":   bundle.get("trained_at", "")[:10],
            "threshold":    int(bundle.get("threshold", 0.03) * 100),
            "importance":   importance[:15],
            "n_features":   len(feature_cols),
            "n_tickers":    len(ticker_cols),
        })
        return ctx
    """On-demand data refresh — fetches latest prices and news, updates MongoDB."""

    def post(self, request):
        try:
            from dashboard.pipeline import run_refresh
            run_refresh()
            return JsonResponse({"status": "ok",
                                 "message": "Data refreshed successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
