import os
import glob
import warnings
import pandas as pd 
from src.data.feature_engineering import build_feature_matrix
from src.future.future_races import build_future_race_frame, save_future_races
from src.future.prepare_future import prepare_future_for_prediction
from src.models.random_forest import train_model, get_feature_importance
from src.models.monte_carlo import run_simulation
from src.models.test import backtest_race
from src.future.predict_future import (
    load_future_races, list_future_races, get_race_rows, predict_future_race,
)
from src.visualizations.position_heatmap import plot_position_heatmap
from src.visualizations.podium_probabilities import plot_podium_probabilities
from src.visualizations.feature_importance import plot_feature_importance
from src.models.track_calibration import calibrate_track_events, get_track_params


# Anchor every data path to the project root so they resolve no matter where
# python is launched from. This is why output reliably lands in data/processed/.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "processed", "master_race_data.csv")
FEATURES_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "processed", "feature_matrix.csv")
SEASONS_DIR = os.path.join(BASE_DIR, "data", "processed", "seasons")
FUTURE_PATH = os.path.join(BASE_DIR, "data", "processed", "future_races.csv")

# Set to a specific year to force a test season
    # leave None to auto-use the most recent season (2026) present in the data.
TEST_SEASON_OVERRIDE = 2024


def _is_stale(cache_path, source_paths):
    """True if the cache is missing or older than its newest source file."""
    if not os.path.exists(cache_path):
        return True
    if not source_paths:
        return False
    return os.path.getmtime(cache_path) < max(os.path.getmtime(p) for p in source_paths)


def run_pipeline():
    os.makedirs(os.path.dirname(DATA_OUTPUT_PATH), exist_ok=True)
    season_files = sorted(glob.glob(os.path.join(SEASONS_DIR, "season_*.csv")))

    if not season_files:
        if os.path.exists(DATA_OUTPUT_PATH):
            print(f"No season files found; loading existing {DATA_OUTPUT_PATH}")
            return pd.read_csv(DATA_OUTPUT_PATH)
        raise FileNotFoundError(
            f"No season files in {SEASONS_DIR}. "
            f"Run `python update_seasons.py` (once per season) to pull the data first."
        )

    # Use the cached master only if it's newer than every season file.
    if os.path.exists(DATA_OUTPUT_PATH) and not _is_stale(DATA_OUTPUT_PATH, season_files):
        print(f"Loading cached dataset from {DATA_OUTPUT_PATH}")
        return pd.read_csv(DATA_OUTPUT_PATH)

    print(f"Assembling master dataset from {len(season_files)} season files...")
    df = pd.concat([pd.read_csv(f) for f in season_files], ignore_index=True)
    df.to_csv(DATA_OUTPUT_PATH, index=False)
    print(f"Master dataset: {len(df)} rows, {df['Year'].nunique()} seasons, "
          f"{df['CircuitName'].nunique()} circuits")
    return df


def run_features(df):
    # Rebuild features if the master is newer than the cached feature matrix.
    if os.path.exists(FEATURES_OUTPUT_PATH) and not _is_stale(FEATURES_OUTPUT_PATH, [DATA_OUTPUT_PATH]):
        print(f"Loading cached features from {FEATURES_OUTPUT_PATH}")
        return pd.read_csv(FEATURES_OUTPUT_PATH)
    df = build_feature_matrix(df)
    df.to_csv(FEATURES_OUTPUT_PATH, index=False)
    return df


def resolve_test_season(df):
    """Most recent season in the data, unless an override is set."""
    seasons = sorted(int(y) for y in df["Year"].unique())
    if len(seasons) < 2:
        raise SystemExit(
            f"Need at least 2 seasons to train + test; only have {seasons}. "
            f"Pull more with `python update_seasons.py`."
        )
    if TEST_SEASON_OVERRIDE is not None:
        if TEST_SEASON_OVERRIDE not in seasons:
            raise SystemExit(
                f"TEST_SEASON_OVERRIDE={TEST_SEASON_OVERRIDE} not in available seasons {seasons}."
            )
        return TEST_SEASON_OVERRIDE
    return seasons[-1]


def run_model(df, test_season):
    model, test_df, metrics = train_model(df, test_season)
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


def ensure_future_file():
    """Build data/processed/future_races.csv if missing or stale, then return its path.
    Runs the future_races + prepare_future steps in-process so the user only runs main.py."""
    season_files = sorted(glob.glob(os.path.join(SEASONS_DIR, "season_*.csv")))
    if os.path.exists(FUTURE_PATH) and not _is_stale(FUTURE_PATH, season_files):
        print(f"Using existing upcoming-race data: {FUTURE_PATH}")
        return FUTURE_PATH

    print("Building upcoming-race data (schedule + expected lineup)...")
    staged = build_future_race_frame(n=2)
    save_future_races(staged, FUTURE_PATH)          # staged rows -> data/processed

    print("Preparing features for upcoming races...")
    prepared = prepare_future_for_prediction(FUTURE_PATH)
    prepared.to_csv(FUTURE_PATH, index=False)        # overwrite with model-ready rows
    print(f"Wrote {len(prepared)} prepared rows -> {FUTURE_PATH}")
    return FUTURE_PATH


def run_future(model, track_calibration):
    path = ensure_future_file()
    future = load_future_races(path)
    races = list_future_races(future).reset_index(drop=True)

    print("\nUpcoming races:")
    for i, row in races.iterrows():
        print(f"  [{i}] R{int(row['RoundNumber'])} {row['CircuitName']} "
              f"({int(row['DriverCount'])} drivers)")

    try:
        pick = int(input("\nPick race index: "))
    except ValueError:
        pick = 0
    pick = pick if 0 <= pick < len(races) else 0

    chosen = races.iloc[pick]
    race_rows = get_race_rows(future, int(chosen["Year"]), int(chosen["RoundNumber"]))

    results = predict_future_race(model, race_rows, track_calibration)

    print(f"\n{'='*70}")
    print(f"  FUTURE PREDICTION — {results['circuit']}  (grid mode: {results['mode'].upper()})")
    print(f"{'='*70}")
    if results["mode"] == "sampled":
        print("  Note: grid is a placeholder form-based draw, not a real qualifying model.")
    print_mc_results(results)


def print_mc_results(results):
    summary = results["summary"].copy()
    summary["PredictedRank"] = range(1, len(summary) + 1)

    print(f"\n{'='*56}")
    print(f"  MONTE CARLO RESULTS ({len(summary)} drivers)")
    print(f"{'='*56}")
    print(f"\n{'#':>3} {'Drv':<4} {'Pos':>4} {'Win':>5} {'Pod':>5} {'Pts':>5} {'xPts':>5}")
    print("-" * 56)
    for _, r in summary.iterrows():
        print(f"{int(r['PredictedRank']):>3} {r['Driver']:<4} "
              f"{r['ExpectedPosition']:>4.0f} "
              f"{r['WinProb']:>4.0f}% {r['PodiumProb']:>4.0f}% "
              f"{r['PointsProb']:>4.0f}% {r['ExpectedPoints']:>5.1f}")

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
    save_dir = os.path.join(BASE_DIR, "outputs", "sim_results")
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

    TEST_SEASON = resolve_test_season(df)
    print(f"\nSeasons available: {sorted(int(y) for y in df['Year'].unique())} "
          f"-> testing on {TEST_SEASON}")

    print("\n[Phase 3] Training model...")
    model, test_df, metrics, importance = run_model(df, TEST_SEASON)
    print_model_metrics(metrics)
    print_feature_importance(importance)

    print("\nCalibrating track-specific event rates...")
    raw_df = pd.read_csv(DATA_OUTPUT_PATH)
    track_calibration = calibrate_track_events(raw_df)

    choice = input("\nMode — [1] backtest a past race  [2] predict an upcoming race: ").strip()
    if choice == "2":
        run_future(model, track_calibration)
    else:
        print("\n[Phase 4] Monte Carlo simulation...")
        results, race_data, circuit, total_laps, track_params = run_sim(model, test_df, track_calibration)
        print_mc_results(results)

        print("\n[Phase 6] Accuracy check...")
        comparison = results["summary"][["Driver", "ExpectedPosition", "WinProb", "PodiumProb"]].copy()
        actuals = race_data[["Driver", "FinishPosition"]].copy()
        comparison = comparison.merge(actuals, on="Driver")
        comparison["Error"] = abs(comparison["ExpectedPosition"] - comparison["FinishPosition"])
        comparison = comparison.sort_values("ExpectedPosition")
        print_accuracy(comparison, circuit)

        run_full = input("\nRun full season backtest? (y/n): ").strip().lower()
        if run_full == "y":
            print(f"\n[Full Backtest] Running MC on all {TEST_SEASON} races...")
            run_full_backtest(test_df, track_calibration)