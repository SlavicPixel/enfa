import joblib
import numpy as np
import pandas as pd
from django.conf import settings

_bundle = None

def get_bundle():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(settings.MODEL_PATH)
    return _bundle


def predict(ticker: str, feature_row: dict) -> dict:
    bundle    = get_bundle()
    model     = bundle["model"]
    scaler    = bundle["scaler"]
    feat_cols = bundle["feature_columns"]

    row = {}
    for col in feat_cols:
        if col.startswith("tkr_"):
            row[col] = 1 if col.replace("tkr_", "") == ticker else 0
        else:
            row[col] = feature_row.get(col, 0.0)

    X    = pd.DataFrame([row])[feat_cols].values
    X_sc = scaler.transform(X)
    prob = float(model.predict_proba(X_sc)[0, 1])

    return {
        "ticker":      ticker,
        "volatile":    prob >= 0.5,
        "probability": round(prob * 100, 1),
        "threshold":   bundle["threshold"],
    }
