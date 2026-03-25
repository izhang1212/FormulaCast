import os
import pandas as pd
from src.data_pipeline import build_master_dataset
from src.feature_engineering import build_feature_matrix
from src.random_forest import train_model, get_feature_importance

DATA_OUTPUT_PATH = os.path.join("data", "processed", "master_race_data.csv")
FEATURES_OUTPUT_PATH = os.path.join("data", "processed", "feature_matrix.csv")
TEST_SEASON = 2025


def run_pipeline():
    """Phase 1: Build the master dataset."""
    os.makedirs(os.path.dirname(DATA_OUTPUT_PATH), exist_ok=True)

    if os.path.exists(DATA_OUTPUT_PATH):
        print(f"Loading cached dataset from {DATA_OUTPUT_PATH}")
        return pd.read_csv(DATA_OUTPUT_PATH)

    df = build_master_dataset()
    df.to_csv(DATA_OUTPUT_PATH, index=False)
    print(f"Saved to {DATA_OUTPUT_PATH}")
    return df


def run_features(df: pd.DataFrame):
    """Phase 2: Build feature matrix."""
    if os.path.exists(FEATURES_OUTPUT_PATH):
        print(f"Loading cached features from {FEATURES_OUTPUT_PATH}")
        return pd.read_csv(FEATURES_OUTPUT_PATH)

    df = build_feature_matrix(df)
    df.to_csv(FEATURES_OUTPUT_PATH, index=False)
    print(f"Saved to {FEATURES_OUTPUT_PATH}")
    return df


def run_model(df: pd.DataFrame):
    """Phase 3: Train and evaluate the RF model."""
    model, test_df, metrics = train_model(df, TEST_SEASON)
    importance = get_feature_importance(model)
    return model, test_df, metrics


if __name__ == "__main__":
    df = run_pipeline()
    df = run_features(df)
    model, test_df, metrics = run_model(df)