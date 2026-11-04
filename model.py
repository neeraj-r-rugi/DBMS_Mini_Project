import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import joblib


df = pd.read_csv("used_cars_dataset_v2.csv")


import pandas as pd

# Remove exact duplicate records
df = df.drop_duplicates().copy()

# Parse asking price into rupees
df["AskPrice"] = pd.to_numeric(
    df["AskPrice"].astype(str)
      .str.replace(r"[^\d.]", "", regex=True),
    errors="coerce"
)

# Parse mileage into kilometres
df["kmDriven"] = pd.to_numeric(
    df["kmDriven"].astype(str)
      .str.replace(r"[^\d.]", "", regex=True),
    errors="coerce"
)

# Standardise categorical values
categorical_cols = [
    "Brand", "model", "Transmission", "Owner", "FuelType"
]

for col in categorical_cols:
    df[col] = df[col].astype("string").str.strip()

# Case-insensitive normalisation
for col in categorical_cols:
    df[col] = df[col].str.lower()

# Drop missing/invalid targets
df = df.dropna(subset=["AskPrice", "Year"])
df = df[df["AskPrice"] > 0].copy()

# Remove clearly invalid manufacturing years.
# 1980 is a conservative lower bound for this initial model;
# revisit it if the dataset genuinely contains classic cars.
df = df[df["Year"].between(1980, 2024)].copy()



# Remove duplicates again after normalisation
df = df.drop_duplicates().copy()


# Remove exact duplicates
df = df.drop_duplicates().copy()

# Drop suspicious records
df = df[
    (df["kmDriven"].isna() | df["kmDriven"].between(0, 300_000))
    & (df["AskPrice"] >= 50_000)
    & (df["Year"].between(1990, 2024))
].copy()

# Remove duplicates again after cleaning
df = df.drop_duplicates().copy()

print("Rows after cleaning:", len(df))
print("Duplicates remaining:", df.duplicated().sum())
print("Missing mileage:", df["kmDriven"].isna().sum())

brand_models = (
    df.dropna(subset=["Brand", "model"])
      .groupby("Brand")["model"]
      .unique()
      .apply(list)
      .to_dict()
)

print(brand_models)

# Features and target
features = [
    "Brand", "model", "Year", "kmDriven",
    "Transmission", "Owner", "FuelType"
]

X = df[features]
y = df["AskPrice"]


# Drop rows with missing mileage
df = df.dropna(subset=["kmDriven"]).copy()

print("Final dataset shape:", df.shape)
print("Missing values:\n", df.isnull().sum())

# Features and target
features = [
    "Brand",
    "model",
    "Year",
    "kmDriven",
    "Transmission",
    "Owner",
    "FuelType"
]

X = df[features]
y = df["AskPrice"]



# Split the dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)


numeric_features = ["Year", "kmDriven"]
categorical_features = [
    "Brand", "model", "Transmission", "Owner", "FuelType"
]

preprocessor = ColumnTransformer([
    (
        "numeric",
        Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ]),
        numeric_features
    ),
    (
        "categorical",
        OneHotEncoder(handle_unknown="ignore"),
        categorical_features
    )
])

knn = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", KNeighborsRegressor(
        n_neighbors=7,
        weights="distance",
        p=2,
        n_jobs=-1
    ))
])

knn.fit(X_train, y_train)
predictions = knn.predict(X_test)

for k in [3, 5, 7, 9, 11, 15, 21]:
    knn = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", KNeighborsRegressor(
            n_neighbors=k,
            weights="distance",
            p=2,
            n_jobs=-1
        ))
    ])

    knn.fit(X_train, y_train)
    pred = knn.predict(X_test)

    mae = mean_absolute_error(y_test, pred)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    r2 = r2_score(y_test, pred)

    print(
        f"k={k:2d} | MAE=₹{mae:,.0f} "
        f"| RMSE=₹{rmse:,.0f} | R²={r2:.4f}"
    )


joblib.dump(knn, "used_cars_knn_model.pkl")