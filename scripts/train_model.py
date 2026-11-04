"""Train the appraisal model from the bundled used-car dataset.

Run from the project root:
    python scripts/train_model.py
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "used_cars_dataset_v2.csv"
ARTIFACT = ROOT / "used_cars_knn_model.pkl"
FEATURES = ["Brand", "model", "Year", "kmDriven", "Transmission", "Owner", "FuelType"]
CATEGORICAL_FEATURES = ["Brand", "model", "Transmission", "Owner", "FuelType"]
NUMERIC_FEATURES = ["Year", "kmDriven"]


def load_training_data() -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.read_csv(DATASET).drop_duplicates().copy()
    frame["AskPrice"] = pd.to_numeric(
        frame["AskPrice"].astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )
    frame["kmDriven"] = pd.to_numeric(
        frame["kmDriven"].astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype("string").str.strip().str.lower()
    frame = frame.dropna(subset=["AskPrice", "Year", "kmDriven"])
    frame = frame[
        frame["AskPrice"].gt(0)
        & frame["AskPrice"].ge(50_000)
        & frame["Year"].between(1990, 2024)
        & frame["kmDriven"].between(0, 300_000)
    ].drop_duplicates()
    return frame[FEATURES], frame["AskPrice"]


def build_pipeline(neighbors: int = 7) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "regressor",
                KNeighborsRegressor(
                    n_neighbors=neighbors, weights="distance", p=2, n_jobs=-1
                ),
            ),
        ]
    )


def main() -> None:
    features, target = load_training_data()
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42
    )
    model = build_pipeline()
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    print(f"Rows after cleaning: {len(features)}")
    print(f"MAE: ₹{mean_absolute_error(y_test, predictions):,.0f}")
    print(f"RMSE: ₹{np.sqrt(mean_squared_error(y_test, predictions)):,.0f}")
    print(f"R²: {r2_score(y_test, predictions):.4f}")
    joblib.dump(model, ARTIFACT)
    print(f"Saved model to {ARTIFACT}")


if __name__ == "__main__":
    main()
