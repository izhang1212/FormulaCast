"""
predict_future.py — Functions to predict an upcoming race from the prepared future frame.

The RF predicts a RESIDUAL relative to GridPosition (PredictedPosition =
GridPosition + residual), so a grid is required. Two modes, one seam:
  - official : race is past qualifying -> pull real GridPosition from FastF1.
  - sampled  : pre-qualifying -> no real grid exists, so each iteration races a
               plausible grid. The grid here is a placeholder form-based draw;
               the future quali model slots into sample_grid() unchanged.
All I/O and printing live in main.py — this module only computes.
"""

import os
import numpy as np
import pandas as pd
import fastf1

from config import CACHE_DIR, NUM_SIMULATIONS, POINTS_SYSTEM
from src.data.feature_engineering import FEATURE_COLUMNS
from src.models.monte_carlo import run_simulation
from src.models.track_calibration import get_track_params

fastf1.Cache.enable_cache(CACHE_DIR)

FUTURE_PATH = os.path.join("data", "processed", "future_races.csv")
DEFAULT_TOTAL_LAPS = 57   # future sessions have no lap count yet; refine per-circuit later


def load_future_races(future_path: str = FUTURE_PATH) -> pd.DataFrame:
    if not os.path.exists(future_path):
        raise FileNotFoundError(
            f"{future_path} not found — run future_races.py then prepare_future.py first."
        )
    return pd.read_csv(future_path)


def list_future_races(future: pd.DataFrame) -> pd.DataFrame:
    """One row per upcoming race for selection/display in main.py."""
    return (future.groupby(["Year", "RoundNumber", "CircuitName"])
            .size().reset_index(name="DriverCount")
            .sort_values(["Year", "RoundNumber"]))


def get_race_rows(future: pd.DataFrame, year: int, rnd: int) -> pd.DataFrame:
    return future[(future["Year"] == year) & (future["RoundNumber"] == rnd)].copy()


def detect_grid_mode(race_rows: pd.DataFrame) -> str:
    """official if qualifying has already happened, else sampled."""
    q = race_rows["QualifyingDateUtc"].iloc[0]
    if pd.isna(q):
        return "sampled"
    q = pd.to_datetime(q)
    if q.tzinfo is not None:
        q = q.tz_localize(None)
    return "official" if q < pd.Timestamp.utcnow().tz_localize(None) else "sampled"


def fill_official_grid(race_rows: pd.DataFrame) -> pd.DataFrame:
    """Pull the real penalty-adjusted grid from the race session results."""
    year = int(race_rows["Year"].iloc[0])
    rnd = int(race_rows["RoundNumber"].iloc[0])
    session = fastf1.get_session(year, rnd, "R")
    session.load(telemetry=False, weather=False, messages=False)
    grid = session.results[["Abbreviation", "GridPosition"]].rename(
        columns={"Abbreviation": "Driver"}
    )
    return race_rows.drop(columns=["GridPosition"]).merge(grid, on="Driver", how="left")


def sample_grid(race_rows: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Placeholder pre-weekend grid: rank by recent form (EWM_Finish) + noise.
    Replace this body with the quali model later — keep the signature identical."""
    out = race_rows.copy()
    form = out["EWM_Finish"].fillna(out["EWM_Finish"].median()).to_numpy()
    noisy = form + rng.normal(0, 2.5, len(out))
    out["GridPosition"] = pd.Series(noisy, index=out.index).rank(method="first").astype(int)
    return out


def _predict_with_grid(model, race_rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the residual model on rows that already have GridPosition filled."""
    X = race_rows[FEATURE_COLUMNS].fillna(0)
    out = race_rows.copy()
    out["PredictedPosition"] = (out["GridPosition"] + model.predict(X)).clip(1, len(out))
    return out.sort_values("PredictedPosition")


def _summary_from_probs(drivers: list, position_probs: np.ndarray) -> pd.DataFrame:
    rows = []
    n = len(drivers)
    pos_range = np.arange(n + 1)
    for i, d in enumerate(drivers):
        p = position_probs[i]
        rows.append({
            "Driver": d,
            "ExpectedPosition": round(float((pos_range * p).sum()), 1),
            "WinProb": round(float(p[1]) * 100, 1),
            "PodiumProb": round(float(p[1:4].sum()) * 100, 1),
            "PointsProb": round(float(p[1:11].sum()) * 100, 1),
            "ExpectedPoints": round(float(sum(POINTS_SYSTEM.get(k, 0) * p[k]
                                              for k in range(1, n + 1))), 2),
        })
    return pd.DataFrame(rows).sort_values("ExpectedPosition")


def predict_future_race(model, race_rows: pd.DataFrame, track_calibration,
                        n_sims: int = NUM_SIMULATIONS, seed: int = 0,
                        total_laps: int = DEFAULT_TOTAL_LAPS) -> dict:
    """Predict one upcoming race. Returns dict with keys:
    summary, position_probs, mode, circuit. No printing."""
    mode = detect_grid_mode(race_rows)
    circuit = race_rows["CircuitName"].iloc[0]
    track_params = get_track_params(track_calibration, circuit)

    if mode == "official":
        graded = _predict_with_grid(model, fill_official_grid(race_rows))
        results = run_simulation(graded[["Driver", "PredictedPosition"]],
                                 total_laps, n_sims=n_sims, track_params=track_params)
        results["mode"] = mode
        results["circuit"] = circuit
        return results

    # Sampled mode: redraw the grid across batches so grid uncertainty is marginalized.
    rng = np.random.default_rng(seed)
    drivers = sorted(race_rows["Driver"].tolist())
    n_drivers = len(drivers)
    idx = {d: i for i, d in enumerate(drivers)}
    accum = np.zeros((n_drivers, n_drivers + 1))
    n_batches = 10
    per_call = max(200, n_sims // n_batches)

    for _ in range(n_batches):
        graded = _predict_with_grid(model, sample_grid(race_rows, rng))
        res = run_simulation(graded[["Driver", "PredictedPosition"]],
                             total_laps, n_sims=per_call, track_params=track_params)
        probs = res["position_probs"]
        for d in drivers:
            accum[idx[d]] += probs.loc[d].to_numpy() * per_call

    position_probs = accum / accum.sum(axis=1, keepdims=True)
    return {
        "summary": _summary_from_probs(drivers, position_probs),
        "position_probs": pd.DataFrame(position_probs, index=drivers,
                                       columns=[f"P{i}" for i in range(n_drivers + 1)]),
        "mode": mode,
        "circuit": circuit,
    }