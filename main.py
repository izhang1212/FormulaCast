import os
import warnings
import pandas as pd
from src.data.data_pipeline import build_master_dataset
from src.data.feature_engineering import build_feature_matrix
from src.models.random_forest import train_model, get_feature_importance
from src.models.monte_carlo import run_simulation
from src.models.test import backtest_race
from src.visualizations.position_heatmap import plot_position_heatmap
from src.visualizations.podium_probabilities import plot_podium_probabilities
from src.visualizations.feature_importance import plot_feature_importance
from src.models.track_calibration import calibrate_track_events, get_track_params

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


def run_sim(model, test_df, track_calibration):
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

    track_params = get_track_params(track_calibration, circuit)

    print(f"\nSimulating: {circuit} ({total_laps} laps)")
    print(f"  SC prob/lap: {track_params['sc_prob_per_lap']:.3f} | "
          f"Lap 1 incident: {track_params['first_lap_incident_rate']:.3f} | "
          f"Mech DNF: {track_params['mechanical_dnf_rate']:.3f}")

    results = run_simulation(race_data, total_laps, track_params=track_params)
    return results, race_data, circuit, total_laps, track_params


def print_mc_results(results):
    summary = results["summary"].copy()
    summary["PredictedRank"] = range(1, len(summary) + 1)

    print(f"\n{'='*70}")
    print(f"  MONTE CARLO RESULTS ({len(summary)} drivers)")
    print(f"{'='*70}")
    print(f"\n{'Driver':<8} {'Rank':>5} {'E[Pos]':>7} {'Win%':>6} {'Podium%':>8} {'Points%':>8} {'E[Pts]':>7}")
    print("-" * 60)
    for _, row in summary.iterrows():
        print(f"{row['Driver']:<8} P{int(row['PredictedRank']):<4} {row['ExpectedPosition']:>7.1f} {row['WinProb']:>5.1f}% "
              f"{row['PodiumProb']:>7.1f}% {row['PointsProb']:>7.1f}% {row['ExpectedPoints']:>7.2f}")


def print_model_metrics(metrics):
    print(f"\n{'='*60}")
    print(f"  MODEL PERFORMANCE")
    print(f"{'='*60}")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

def print_feature_importance(importance):
    print(f"\n{'='*60}")
    print(f"  FEATURE IMPORTANCES")
    print(f"{'='*60}")
    for _, row in importance.iterrows():
        bar = "█" * int(row["Importance"] * 100)
        print(f"  {row['Feature']:30s} {row['Importance']:.4f} {bar}")

def print_accuracy(comparison, circuit):
    comparison = comparison.copy()
    comparison["PredictedRank"] = comparison["ExpectedPosition"].rank(method="first").astype(int)

    print(f"\n{'='*70}")
    print(f"  ACCURACY CHECK — {circuit}")
    print(f"{'='*70}")
    print(f"\n{'Driver':<8} {'Rank':>5} {'Predicted':>10} {'Actual':>8} {'Error':>7}")
    print("-" * 45)
    for _, row in comparison.iterrows():
        print(f"{row['Driver']:<8} P{int(row['PredictedRank']):<4} {row['ExpectedPosition']:>10.1f} "
              f"{int(row['FinishPosition']):>8} {row['Error']:>7.1f}")

    top_10 = comparison.nsmallest(10, "FinishPosition")

    mae = comparison["Error"].mean()
    top_10_mae = top_10["Error"].mean()
    within_1 = (comparison["Error"] <= 1).mean() * 100
    within_3 = (comparison["Error"] <= 3).mean() * 100
    within_5 = (comparison["Error"] <= 5).mean() * 100

    print(f"\n  Overall MAE:        {mae:.2f} positions")
    print(f"  Top 10 MAE:         {top_10_mae:.2f} positions")
    print(f"  Within 1 position:  {within_1:.1f}%")
    print(f"  Within 3 positions: {within_3:.1f}%")
    print(f"  Within 5 positions: {within_5:.1f}%")


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

def run_full_backtest(test_df, track_calibration):
    races = test_df.groupby(["Year", "RoundNumber", "CircuitName"])
    all_comparisons = []

    for (year, rnd, circuit), race_data in races:
        total_laps = int(race_data["TotalRaceLaps"].iloc[0]) if "TotalRaceLaps" in race_data.columns else 57
        track_params = get_track_params(track_calibration, circuit)

        print(f"  Backtesting Round {int(rnd)}: {circuit}...", end=" ")

        results = run_simulation(race_data, total_laps, n_sims=3000, track_params=track_params)
        summary = results["summary"]

        comparison = summary[["Driver", "ExpectedPosition"]].merge(
            race_data[["Driver", "FinishPosition"]], on="Driver"
        )
        comparison["Error"] = abs(comparison["ExpectedPosition"] - comparison["FinishPosition"])
        comparison["Circuit"] = circuit
        comparison["Round"] = rnd
        all_comparisons.append(comparison)

        print(f"MAE: {comparison['Error'].mean():.2f}")

    full = pd.concat(all_comparisons, ignore_index=True)
    top_10 = full[full["FinishPosition"] <= 10]

    print(f"\n{'='*60}")
    print(f"  FULL SEASON BACKTEST")
    print(f"{'='*60}")
    print(f"  Races tested:        {len(all_comparisons)}")
    print(f"  Overall MAE:         {full['Error'].mean():.2f} positions")
    print(f"  Top 10 MAE:          {top_10['Error'].mean():.2f} positions")
    print(f"  Median error:        {full['Error'].median():.1f} positions")
    print(f"  Within 1 position:   {(full['Error'] <= 1).mean() * 100:.1f}%")
    print(f"  Within 3 positions:  {(full['Error'] <= 3).mean() * 100:.1f}%")
    print(f"  Within 5 positions:  {(full['Error'] <= 5).mean() * 100:.1f}%")

    race_mae = full.groupby("Circuit")["Error"].mean().sort_values()
    print(f"\n  Best race:  {race_mae.index[0]} (MAE: {race_mae.iloc[0]:.2f})")
    print(f"  Worst race: {race_mae.index[-1]} (MAE: {race_mae.iloc[-1]:.2f})")

    return full


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
    print_feature_importance(importance)

    print("\nCalibrating track-specific event rates...")
    raw_df = pd.read_csv(DATA_OUTPUT_PATH)
    track_calibration = calibrate_track_events(raw_df)

    print("\n[Phase 4] Monte Carlo simulation...")
    results, race_data, circuit, total_laps, track_params = run_sim(model, test_df, track_calibration)
    print_mc_results(results)

    print("\n[Phase 6] Accuracy check...")
    comparison = results["summary"][["Driver", "ExpectedPosition", "WinProb", "PodiumProb"]].copy()
    actuals = race_data[["Driver", "FinishPosition"]].copy()
    comparison = comparison.merge(actuals, on="Driver")
    comparison["Error"] = abs(comparison["ExpectedPosition"] - comparison["FinishPosition"])
    comparison = comparison.sort_values("FinishPosition")
    print_accuracy(comparison, circuit)

    run_full = input("\nRun full season backtest? (y/n): ").strip().lower()
    if run_full == "y":
        print("\n[Full Backtest] Running MC on all 2025 races...")
        backtest_full = run_full_backtest(test_df, track_calibration)