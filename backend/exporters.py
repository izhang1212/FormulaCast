"""
FormulaCast export commands.

Run from the project root:
    python -m backend.exporters historical
    python -m backend.exporters future
    python -m backend.exporters performance
    python -m backend.exporters all
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.config import DATA_ROOT, RF_PARAMS
from backend.main import (
    BASE_DIR,
    DATA_OUTPUT_PATH,
    ensure_future_file,
    run_features,
    run_model,
    run_pipeline,
)
from backend.src.data.feature_engineering import FEATURE_COLUMNS
from backend.src.future.predict_future import (
    get_race_rows,
    list_future_races,
    load_future_races,
    predict_future_race,
)
from backend.src.models.monte_carlo import COLUMN_MAP, export_index, export_race, run_simulation
from backend.src.models.track_calibration import calibrate_track_events, get_track_params


PREDICTIONS_DIR = Path(DATA_ROOT) / "predictions"
FUTURE_DIR = PREDICTIONS_DIR / "future"
PERFORMANCE_PATH = PREDICTIONS_DIR / "performance.json"


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def export_historical_predictions():
    """Simulate every predictable historical season and write race JSON."""
    print("Loading data + features...")
    df = run_pipeline()
    df = run_features(df)

    raw_df = pd.read_csv(DATA_OUTPUT_PATH)
    track_calibration = calibrate_track_events(raw_df)

    seasons = sorted(int(y) for y in df["Year"].unique())
    index = []

    for season in seasons:
        if not [s for s in seasons if s < season]:
            print(f"Skipping {season}: no prior season to train on.")
            continue

        try:
            model, test_df, metrics, importance = run_model(df, season)
        except Exception as e:
            print(f"Skipping {season}: training failed ({e}).")
            continue

        year_dir = PREDICTIONS_DIR / str(season)
        races = (
            test_df.groupby(["RoundNumber", "CircuitName"])
            .size()
            .reset_index()
            .sort_values("RoundNumber")
        )

        for _, row in races.iterrows():
            rnd = int(row["RoundNumber"])
            circuit = row["CircuitName"]
            race_data = test_df[test_df["RoundNumber"] == rnd].copy()
            total_laps = (
                int(race_data["TotalRaceLaps"].iloc[0])
                if "TotalRaceLaps" in race_data.columns
                else 57
            )
            track_params = get_track_params(track_calibration, circuit)

            print(f"  {season} R{rnd}: {circuit} ({total_laps} laps)...", end=" ")
            results = run_simulation(race_data, total_laps, track_params=track_params)
            export_race(
                results["summary"],
                season,
                rnd,
                circuit,
                total_laps,
                year_dir,
                actuals_df=race_data,
            )
            index.append({"year": season, "round": rnd, "name": circuit})
            print("done")

    export_index(index, PREDICTIONS_DIR)
    years = sorted({i["year"] for i in index})
    print(f"\nWrote {len(index)} races across seasons {years}.")


def train_model_on_all_history(features: pd.DataFrame):
    train = features.dropna(subset=["FinishPosition", "GridPosition"]).copy()
    train["Residual"] = train["FinishPosition"] - train["GridPosition"]

    model = RandomForestRegressor(**RF_PARAMS)
    model.fit(train[FEATURE_COLUMNS].fillna(0), train["Residual"])
    return model


def export_future_race(results: dict, year: int, round_no: int, name: str, race_rows: pd.DataFrame):
    FUTURE_DIR.mkdir(parents=True, exist_ok=True)

    summary = results["summary"].rename(columns=COLUMN_MAP)
    payload = {
        "year": year,
        "round": round_no,
        "name": name,
        "laps": int(results.get("total_laps", 57)),
        "mode": results.get("mode", "sampled"),
        "race_date": race_rows["RaceDateUtc"].iloc[0] if "RaceDateUtc" in race_rows else None,
        "qualifying_date": race_rows["QualifyingDateUtc"].iloc[0] if "QualifyingDateUtc" in race_rows else None,
        "drivers": summary.to_dict(orient="records"),
    }

    path = FUTURE_DIR / f"{year}_round_{round_no}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=_json_default)
    return path


def export_future_predictions():
    """Train on completed history and export the next upcoming races."""
    print("Loading historical data + features...")
    history = run_pipeline()
    features = run_features(history)
    raw_df = pd.read_csv(DATA_OUTPUT_PATH)

    print("Training final model on all completed historical rows...")
    model = train_model_on_all_history(features)
    track_calibration = calibrate_track_events(raw_df)

    print("Preparing upcoming race frame...")
    future_path = ensure_future_file()
    future = load_future_races(future_path)
    races = list_future_races(future).reset_index(drop=True)

    index = []
    for _, race in races.iterrows():
        year = int(race["Year"])
        round_no = int(race["RoundNumber"])
        name = race["CircuitName"]
        rows = get_race_rows(future, year, round_no)

        print(f"  {year} R{round_no}: {name}...", end=" ")
        results = predict_future_race(model, rows, track_calibration)
        export_future_race(results, year, round_no, name, rows)
        index.append({
            "year": year,
            "round": round_no,
            "name": name,
            "mode": results.get("mode", "sampled"),
            "race_date": rows["RaceDateUtc"].iloc[0] if "RaceDateUtc" in rows else None,
            "qualifying_date": rows["QualifyingDateUtc"].iloc[0] if "QualifyingDateUtc" in rows else None,
        })
        print("done")

    FUTURE_DIR.mkdir(parents=True, exist_ok=True)
    with open(FUTURE_DIR / "index.json", "w") as f:
        json.dump(index, f, indent=2, default=_json_default)

    print(f"\nWrote {len(index)} future predictions -> {FUTURE_DIR}")


def _feature_label(feature: str) -> str:
    spaced = feature.replace("_", " ")
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    words = []
    for word in spaced.split():
        if word.upper() in {"EWM", "DNF", "FP", "MAE", "RMSE", "PCT"}:
            words.append(word.upper())
        elif word.lower() == "avg":
            words.append("Average")
        elif word.lower() == "quali":
            words.append("Quali")
        else:
            words.append(word.capitalize())
    return " ".join(words)


def _feature_group(feature: str) -> str:
    lowered = feature.lower()
    if "grid" in lowered or "quali" in lowered:
        return "Qualifying"
    if "constructor" in lowered or "team" in lowered:
        return "Team form"
    if "circuit" in lowered or "track" in lowered:
        return "Track history"
    if "pace" in lowered or "practice" in lowered:
        return "Practice pace"
    if "weather" in lowered or "temp" in lowered or "rain" in lowered:
        return "Conditions"
    if "rolling" in lowered or "recent" in lowered or "ewm" in lowered:
        return "Recent form"
    return "Model signal"


def _metric_cards(metrics: dict) -> list[dict]:
    specs = [
        ("MAE", "Mean Abs Error", "pos", "Average finishing-position miss across all walk-forward holdout seasons."),
        ("RMSE", "RMSE", "pos", "Penalizes larger misses more heavily than MAE across all holdout seasons."),
        ("Within_3_Positions", "Within 3", "%", "Share of all holdout predictions within three finishing positions."),
        ("Podium_Accuracy", "Podium Hit Rate", "%", "Average overlap between predicted and real podium drivers."),
        ("Baseline_MAE (Grid Order)", "Grid Baseline", "pos", "Error if each race simply followed qualifying order."),
        ("Improvement_Over_Baseline", "Avg Grid Gain", "pos", "Average model improvement over the grid baseline."),
    ]
    cards = []
    for key, label, unit, detail in specs:
        if key in metrics:
            cards.append({
                "key": key,
                "label": label,
                "value": metrics[key],
                "unit": unit,
                "detail": detail,
            })
    return cards


def _importance_payload(importance: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in importance.iterrows():
        value = float(row["Importance"])
        feature = row["Feature"]
        rows.append({
            "feature": feature,
            "label": _feature_label(feature),
            "group": _feature_group(feature),
            "importance": value,
            "percent": round(value * 100, 2),
        })
    return rows


def _walk_forward_performance(features: pd.DataFrame) -> tuple[dict, pd.DataFrame, list[int]]:
    seasons = sorted(int(year) for year in features["Year"].dropna().unique())
    holdout_seasons = [season for season in seasons if any(prev < season for prev in seasons)]
    predictions = []
    importance_rows = []

    for season in holdout_seasons:
        print(f"Training Random Forest holdout model for {season}...")
        model, test_df, metrics, importance = run_model(features, season)
        if test_df.empty:
            continue

        predictions.append(test_df)
        importance_rows.append(pd.DataFrame({
            "Feature": FEATURE_COLUMNS,
            "Importance": model.feature_importances_,
        }))

    if not predictions:
        return {}, pd.DataFrame(columns=["Feature", "Importance"]), []

    combined = pd.concat(predictions, ignore_index=True)
    y_true = combined["FinishPosition"]
    y_pred = combined["PredictedPosition"]

    podium_correct = 0
    total_podium_slots = 0
    for _, group in combined.groupby(["Year", "RoundNumber"]):
        actual_podium = set(group.nsmallest(3, "FinishPosition")["Driver"])
        predicted_podium = set(group.nsmallest(3, "PredictedPosition")["Driver"])
        podium_correct += len(actual_podium & predicted_podium)
        total_podium_slots += 3

    baseline_mae = mean_absolute_error(y_true, combined["GridPosition"])
    mae = mean_absolute_error(y_true, y_pred)
    metrics = {
        "MAE": round(float(mae), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "Within_3_Positions": round(float(np.mean(np.abs(y_true - y_pred) <= 3) * 100), 1),
        "Podium_Accuracy": round(float((podium_correct / total_podium_slots) * 100), 1)
        if total_podium_slots
        else 0,
        "Baseline_MAE (Grid Order)": round(float(baseline_mae), 2),
        "Improvement_Over_Baseline": round(float(baseline_mae - mae), 2),
    }

    importance = (
        pd.concat(importance_rows, ignore_index=True)
        .groupby("Feature", as_index=False)["Importance"]
        .mean()
        .sort_values("Importance", ascending=False)
        .head(15)
    )

    return metrics, importance, holdout_seasons


def _prediction_accuracy() -> dict:
    race_rows = []
    all_errors = []
    top_10_errors = []

    if not PREDICTIONS_DIR.exists():
        return {
            "race_count": 0,
            "driver_count": 0,
            "overall_mae": None,
            "top_10_mae": None,
            "median_error": None,
            "within_1": None,
            "within_3": None,
            "within_5": None,
            "best_race": None,
            "worst_race": None,
            "race_errors": [],
        }

    for year_dir in sorted(PREDICTIONS_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for path in sorted(year_dir.glob("round_*.json")):
            with open(path) as f:
                race = json.load(f)

            drivers = [d for d in race.get("drivers", []) if d.get("actual") is not None]
            if not drivers:
                continue

            errors = [
                abs(float(driver["expected_position"]) - float(driver["actual"]))
                for driver in drivers
            ]
            race_top_10 = [
                abs(float(driver["expected_position"]) - float(driver["actual"]))
                for driver in drivers
                if float(driver["actual"]) <= 10
            ]

            all_errors.extend(errors)
            top_10_errors.extend(race_top_10)
            race_rows.append({
                "year": int(race["year"]),
                "round": int(race["round"]),
                "name": race["name"],
                "mae": round(float(np.mean(errors)), 2),
                "top_10_mae": round(float(np.mean(race_top_10)), 2) if race_top_10 else None,
                "drivers": len(drivers),
            })

    if not all_errors:
        return {
            "race_count": 0,
            "driver_count": 0,
            "overall_mae": None,
            "top_10_mae": None,
            "median_error": None,
            "within_1": None,
            "within_3": None,
            "within_5": None,
            "best_race": None,
            "worst_race": None,
            "race_errors": [],
        }

    race_rows = sorted(race_rows, key=lambda row: (row["mae"], row["year"], row["round"]))
    return {
        "race_count": len(race_rows),
        "driver_count": len(all_errors),
        "overall_mae": round(float(np.mean(all_errors)), 2),
        "top_10_mae": round(float(np.mean(top_10_errors)), 2) if top_10_errors else None,
        "median_error": round(float(np.median(all_errors)), 1),
        "within_1": round(float(np.mean(np.array(all_errors) <= 1) * 100), 1),
        "within_3": round(float(np.mean(np.array(all_errors) <= 3) * 100), 1),
        "within_5": round(float(np.mean(np.array(all_errors) <= 5) * 100), 1),
        "best_race": race_rows[0],
        "worst_race": race_rows[-1],
        "race_errors": race_rows,
    }


def export_performance():
    """Export model metrics, feature importance, and prediction accuracy."""
    print("Loading data + features...")
    history = run_pipeline()
    features = run_features(history)

    seasons = sorted(int(year) for year in features["Year"].dropna().unique())
    metrics, importance, holdout_seasons = _walk_forward_performance(features)
    accuracy = _prediction_accuracy()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_season": f"{holdout_seasons[0]}-{holdout_seasons[-1]}" if holdout_seasons else None,
        "test_seasons": holdout_seasons,
        "train_seasons": seasons,
        "data": {
            "seasons": seasons,
            "feature_rows": int(len(features)),
            "completed_races": accuracy["race_count"],
            "historical_driver_predictions": accuracy["driver_count"],
        },
        "random_forest": {
            "metrics": metrics,
            "cards": _metric_cards(metrics),
            "feature_importance": _importance_payload(importance),
        },
        "monte_carlo": {
            "accuracy": accuracy,
            "bands": [
                {"label": "Within 1", "value": accuracy["within_1"], "unit": "%"},
                {"label": "Within 3", "value": accuracy["within_3"], "unit": "%"},
                {"label": "Within 5", "value": accuracy["within_5"], "unit": "%"},
            ],
        },
    }

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PERFORMANCE_PATH, "w") as f:
        json.dump(payload, f, indent=2, default=_json_default)

    print(f"Wrote performance export -> {PERFORMANCE_PATH}")


def export_all():
    export_historical_predictions()
    export_future_predictions()
    export_performance()


def main():
    parser = argparse.ArgumentParser(description="Export FormulaCast frontend data")
    parser.add_argument(
        "targets",
        nargs="*",
        choices=["historical", "future", "performance", "all"],
        default=["all"],
        help="Which export(s) to run. Defaults to all.",
    )
    args = parser.parse_args()

    targets = args.targets
    if "all" in targets:
        export_all()
        return

    for target in targets:
        if target == "historical":
            export_historical_predictions()
        elif target == "future":
            export_future_predictions()
        elif target == "performance":
            export_performance()


if __name__ == "__main__":
    main()
