# Random Forest model for predicting base finishing positions

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from config import RF_PARAMS
from src.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMN

# Takes full feature matrix and a year to hold out for testing
    # Returns: Trarined model, test set with predictions, metrics dict
def train_model(df: pd.DataFrame, test_season: int) -> tuple:

    train = df[df["Year"] < test_season].copy()
    test = df[df["Year"] == test_season].copy()

    print(f"Train: {len(train)} rows ({train['Year'].min()}-{train['Year'].max()})")
    print(f"Test:  {len(test)} rows ({test_season})")

    # X: features (i.e. the inputs) Y: the target (i.e. what we are predicting)
    X_train = train[FEATURE_COLUMNS].fillna(0)
    y_train = train[TARGET_COLUMN]
    X_test = test[FEATURE_COLUMNS].fillna(0)
    y_test = test[TARGET_COLUMN]

    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    test["PredictedPosition"] = predictions

    # Metrics
    metrics = evaluate_model(y_test, predictions, test)

    return model, test, metrics

# Calculate performance metrics
def evaluate_model(y_true, y_pred, test_df: pd.DataFrame) -> dict:

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    # Within ±3 positions
    within_3 = np.mean(np.abs(y_true - y_pred) <= 3)

    # Top 3 accuracy: did we predict the right drivers on the podium?
    podium_correct = 0
    total_races = 0
    for (year, rnd), group in test_df.groupby(["Year", "RoundNumber"]):
        actual_podium = set(group.nsmallest(3, "FinishPosition")["Driver"])
        predicted_podium = set(group.nsmallest(3, "PredictedPosition")["Driver"])
        podium_correct += len(actual_podium & predicted_podium)
        total_races += 3
    podium_accuracy = podium_correct / total_races if total_races > 0 else 0

    # Baseline comparison: just predicting grid order
    baseline_mae = mean_absolute_error(y_true, test_df["GridPosition"])

    metrics = {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "Within_3_Positions": round(within_3 * 100, 1),
        "Podium_Accuracy": round(podium_accuracy * 100, 1),
        "Baseline_MAE (Grid Order)": round(baseline_mae, 2),
        "Improvement_Over_Baseline": round(baseline_mae - mae, 2),
    }

    print("\n--- Model Performance ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    return metrics


def get_feature_importance(model, top_n: int = 15) -> pd.DataFrame:
    """Extract and rank feature importances."""
    importance_df = pd.DataFrame({
        "Feature": FEATURE_COLUMNS,
        "Importance": model.feature_importances_,
    }).sort_values("Importance", ascending=False).head(top_n)

    print("\n--- Top Feature Importances ---")
    for _, row in importance_df.iterrows():
        bar = "█" * int(row["Importance"] * 100)
        print(f"  {row['Feature']:30s} {row['Importance']:.4f} {bar}")

    return importance_df


def predict_race(model, race_features: pd.DataFrame) -> pd.DataFrame:
    """
    Given feature data for an upcoming/specific race, predict finishing order.
    Returns DataFrame sorted by predicted position.
    """
    X = race_features[FEATURE_COLUMNS].fillna(0)
    race_features = race_features.copy()
    race_features["PredictedPosition"] = model.predict(X)

    return race_features.sort_values("PredictedPosition")