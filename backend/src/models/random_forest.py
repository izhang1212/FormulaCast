# Random Forest model for predicting base finishing positions

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from backend.config import RF_PARAMS
from backend.src.data.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMN

# Takes full feature matrix and a year to hold out for testing
    # Returns: Trarined model, test set with predictions, metrics dict
def train_model(df: pd.DataFrame, test_season: int) -> tuple:
    train = df[df["Year"] < test_season].copy()
    test = df[df["Year"] == test_season].copy()

    # Remove rows where finishing pos is missing
    train = train.dropna(subset=["FinishPosition"])
    test = test.dropna(subset=["FinishPosition"])

    print(f"Train: {len(train)} rows ({train['Year'].min()}-{train['Year'].max()})")
    print(f"Test:  {len(test)} rows ({test_season})")

    # Predict resisual position (how many positions driver gains/loses)
    train["Residual"] = train["FinishPosition"] - train["GridPosition"]
    test["Residual"] = test["FinishPosition"] - test["GridPosition"]

    # Replaces missing values in predictive features with 0's (since model only accpets numbers)
    X_train = train[FEATURE_COLUMNS].fillna(0)
    y_train = train["Residual"]
    X_test = test[FEATURE_COLUMNS].fillna(0)

    # Create RF model with the params we defined
    model = RandomForestRegressor(**RF_PARAMS)
    # Model looks at all training rows and builds n decision trees
    model.fit(X_train, y_train)

    # Average out predictions
    predicted_residual = model.predict(X_test)
    test["PredictedPosition"] = test["GridPosition"] + predicted_residual
    test["PredictedPosition"] = test["PredictedPosition"].clip(1, 20)

    y_true = test["FinishPosition"]
    y_pred = test["PredictedPosition"]

    metrics = evaluate_model(y_true, y_pred, test)

    return model, test, metrics

# Calculate performance metrics (MAE)
def evaluate_model(y_true, y_pred, test_df: pd.DataFrame) -> dict:
    # Mean Absolute Error: how far off each predicted position was
        # e.g. predicted [3,5,8] vs. actual [2,5,10] has errors [1,0,2] and an MAE of 1
    mae = mean_absolute_error(y_true, y_pred)
    # Root squared mean error
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

    return metrics

# Extract and rank feature importances (i.e. which features contriubted the most to reducing prediction error)
    # A feature with importance 0.15 means it was responsible for 15% of model's predictive power
def get_feature_importance(model, top_n: int = 15) -> pd.DataFrame:
    importance_df = pd.DataFrame({
        "Feature": FEATURE_COLUMNS,
        "Importance": model.feature_importances_,
    }).sort_values("Importance", ascending=False).head(top_n)

    return importance_df
 
# Given feature data for an upcoming/specific race, predict finishing order
    # Returns DataFrame sorted by predicted position (Monte Carlo calls this before adding randomness)
def predict_race(model, race_features: pd.DataFrame) -> pd.DataFrame:
    X = race_features[FEATURE_COLUMNS].fillna(0)
    race_features = race_features.copy()
    predicted_residual = model.predict(X)
    race_features["PredictedPosition"] = (
        race_features["GridPosition"] + predicted_residual
    ).clip(1, len(race_features))
    return race_features.sort_values("PredictedPosition")