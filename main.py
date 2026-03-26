"""
main.py — Entry point for the F1 Race Simulator.
"""

import os
import warnings
import pandas as pd
from src.data.data_pipeline import build_master_dataset
from src.data.feature_engineering import build_feature_matrix
from src.models.random_forest import train_model, get_feature_importance
from src.models.monte_carlo import run_simulation

warnings.filterwarnings("ignore")

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


def run_sim(model, test_df: pd.DataFrame):
    """Phase 4: Run Monte Carlo simulation on a specific race."""
    available_races = test_df.groupby(["Year", "RoundNumber", "CircuitName"]).size().reset_index()

    print("\nAvailable races to simulate:")
    for _, row in available_races.iterrows():
        print(f"  Round {int(row['RoundNumber'])}: {row['CircuitName']}")

    # Let user pick a race
    try:
        choice = int(input("\nEnter round number to simulate (or 0 for first available): "))
    except ValueError:
        choice = 0

    if choice == 0:
        choice = int(available_races.iloc[0]["RoundNumber"])

    race_data = test_df[test_df["RoundNumber"] == choice].copy()

    if race_data.empty:
        print(f"Round {choice} not found, using first available.")
        choice = int(available_races.iloc[0]["RoundNumber"])
        race_data = test_df[test_df["RoundNumber"] == choice].copy()

    circuit = race_data["CircuitName"].iloc[0]
    total_laps = int(race_data["TotalRaceLaps"].iloc[0]) if "TotalRaceLaps" in race_data.columns else 57

    print(f"\nSimulating: {circuit} ({total_laps} laps)")
    print(f"Running 10,000 simulations...\n")

    results = run_simulation(race_data, total_laps)
    return results


if __name__ == "__main__":
    print("=" * 50)
    print("  F1 Race Simulator — FormulaCast")
    print("=" * 50)

    print("\n[Phase 1] Loading data...")
    df = run_pipeline()

    print("\n[Phase 2] Engineering features...")
    df = run_features(df)

    print("\n[Phase 3] Training model...")
    model, test_df, metrics = run_model(df)

    print("\n[Phase 4] Monte Carlo simulation...")
    results = run_sim(model, test_df)