# main.py

import os
import warnings
import pandas as pd
from src.data.data_pipeline import build_master_dataset
from src.data.feature_engineering import build_feature_matrix
from src.models.random_forest import train_model, get_feature_importance
from src.models.monte_carlo import run_simulation
from src.visualizations.position_heatmap import plot_position_heatmap
from src.visualizations.podium_probabilities import plot_podium_probabilities
from src.visualizations.feature_importance import plot_feature_importance

warnings.filterwarnings("ignore")

DATA_OUTPUT_PATH = os.path.join("data", "processed", "master_race_data.csv")
FEATURES_OUTPUT_PATH = os.path.join("data", "processed", "feature_matrix.csv")
TEST_SEASON = 2025


def run_pipeline():
    os.makedirs(os.path.dirname(DATA_OUTPUT_PATH), exist_ok=True)
    if os.path.exists(DATA_OUTPUT_PATH):
        print(f"Loading cached dataset from {DATA_OUTPUT_PATH}")
        return pd.read_csv(DATA_OUTPUT_PATH)
    df = build_master_dataset()
    df.to_csv(DATA_OUTPUT_PATH, index=False)
    return df


def run_features(df):
    if os.path.exists(FEATURES_OUTPUT_PATH):
        print(f"Loading cached features from {FEATURES_OUTPUT_PATH}")
        return pd.read_csv(FEATURES_OUTPUT_PATH)
    df = build_feature_matrix(df)
    df.to_csv(FEATURES_OUTPUT_PATH, index=False)
    return df


def run_model(df):
    model, test_df, metrics = train_model(df, TEST_SEASON)
    importance = get_feature_importance(model)
    return model, test_df, metrics, importance


def run_sim(model, test_df):
    available_races = test_df.groupby(["Year", "RoundNumber", "CircuitName"]).size().reset_index()

    print("\nAvailable races to simulate:")
    for _, row in available_races.iterrows():
        print(f"  Round {int(row['RoundNumber'])}: {row['CircuitName']}")

    try:
        choice = int(input("\nEnter round number to simulate (or 0 for first available): "))
    except ValueError:
        choice = 0

    if choice == 0:
        choice = int(available_races.iloc[0]["RoundNumber"])

    race_data = test_df[test_df["RoundNumber"] == choice].copy()
    if race_data.empty:
        choice = int(available_races.iloc[0]["RoundNumber"])
        race_data = test_df[test_df["RoundNumber"] == choice].copy()

    circuit = race_data["CircuitName"].iloc[0]
    total_laps = int(race_data["TotalRaceLaps"].iloc[0]) if "TotalRaceLaps" in race_data.columns else 57

    print(f"\nSimulating: {circuit} ({total_laps} laps)")

    results = run_simulation(race_data, total_laps)
    return results, race_data, circuit


def print_mc_results(results):
    summary = results["summary"]
    print(f"\n{'='*60}")
    print(f"  MONTE CARLO RESULTS ({len(results['position_probs'])} drivers)")
    print(f"{'='*60}")
    print(f"\n{'Driver':<8} {'E[Pos]':>7} {'Win%':>6} {'Podium%':>8} {'Points%':>8} {'E[Pts]':>7}")
    print("-" * 50)
    for _, row in summary.iterrows():
        print(f"{row['Driver']:<8} {row['ExpectedPosition']:>7.1f} {row['WinProb']:>5.1f}% "
              f"{row['PodiumProb']:>7.1f}% {row['PointsProb']:>7.1f}% {row['ExpectedPoints']:>7.2f}")


def print_model_metrics(metrics):
    print(f"\n{'='*60}")
    print(f"  MODEL PERFORMANCE")
    print(f"{'='*60}")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


def run_visualizations(results, importance, circuit):
    save_dir = os.path.join("outputs", "sim_results")
    os.makedirs(save_dir, exist_ok=True)

    plot_position_heatmap(results["position_probs"], circuit,
                          os.path.join(save_dir, "position_heatmap.html"))
    plot_podium_probabilities(results["summary"], circuit,
                              os.path.join(save_dir, "podium_probs.html"))
    plot_feature_importance(importance,
                            os.path.join(save_dir, "feature_importance.html"))

    print(f"\nCharts saved to {save_dir}/")


if __name__ == "__main__":
    print("=" * 60)
    print("  F1 Race Simulator — FormulaCast")
    print("=" * 60)

    print("\n[Phase 1] Loading data...")
    df = run_pipeline()

    print("\n[Phase 2] Engineering features...")
    df = run_features(df)

    print("\n[Phase 3] Training model...")
    model, test_df, metrics, importance = run_model(df)
    print_model_metrics(metrics)

    print("\n[Phase 4] Monte Carlo simulation...")
    results, race_data, circuit = run_sim(model, test_df)
    print_mc_results(results)

   