from pathlib import Path
from typing import Any, Dict
import pandas as pd
from .config import MODEL_PATH

_model = None

def load_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        try:
            import joblib
            _model = joblib.load(MODEL_PATH)
        except Exception:
            _model = False
    return _model if _model is not False else None

def predict(data: Dict[str, Any]):
    model = load_model()
    if model is not None:
        try:
            row = {"Brand": data["brand"].lower(), "model": data["model"].lower(), "Year": data["year"], "kmDriven": data["km_driven"], "Transmission": data["transmission"].lower(), "Owner": data["owner"].lower(), "FuelType": data["fuel_type"].lower()}
            return float(model.predict(pd.DataFrame([row]))[0]), True
        except Exception:
            pass
    # Useful deterministic demo estimate when artifact/dependencies are unavailable.
    age = max(0, 2024 - data["year"])
    estimate = max(50000.0, 900000.0 * (0.88 ** age) - data["km_driven"] * 0.7)
    return round(estimate, 2), False
