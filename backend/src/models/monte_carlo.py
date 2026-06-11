# Core Monte Carlo simulation engine (optimized).

import numpy as np
import pandas as pd
import json
from pathlib import Path
from backend.config import NUM_SIMULATIONS, MC_RANDOM_SEED, POINTS_SYSTEM
from backend.src.models.race_events import SafetyCarModel


DEFAULT_TRACK_PARAMS = {
    "sc_prob_per_lap": 0.015,
    "first_lap_incident_rate": 0.04,
    "mechanical_dnf_rate": 0.02,
    "avg_pit_stops": 2.0,
}


def compute_dnf_rates(df, track_params, weights=(0.4, 0.35, 0.25), lo=0.01, hi=0.30):
    """Per-driver total race DNF probability.

    Blends the track baseline (first-lap incident + mechanical) with each driver's
    and team's historical DNF rate, so a reliable front-runner retires far less than
    a fragile car. Falls back to the flat track rate when history columns are absent
    (e.g. the predict path only passes Driver + PredictedPosition).
    """
    base = track_params["first_lap_incident_rate"] + track_params["mechanical_dnf_rate"]
    n = len(df)
    drv = df["DNFRate_Last10"].to_numpy() if "DNFRate_Last10" in df.columns else np.full(n, base)
    team = df["TeamDNFRate_Last10"].to_numpy() if "TeamDNFRate_Last10" in df.columns else np.full(n, base)
    drv = np.nan_to_num(drv, nan=base)
    team = np.nan_to_num(team, nan=base)
    rate = weights[0] * base + weights[1] * drv + weights[2] * team
    return np.clip(rate, lo, hi)


def simulate_single_race(drivers: np.ndarray, predicted_positions: np.ndarray,
                         total_laps: int, rng: np.random.Generator,
                         track_params: dict = None,
                         dnf_rates: np.ndarray = None) -> tuple:
    """Simulate one race. Returns (positions, dnf_flags)."""
    n = len(drivers)

    if track_params is None:
        track_params = DEFAULT_TRACK_PARAMS

    # Split each driver's total DNF rate into first-lap vs mid-race in the same
    # proportion the track baseline implies.
    base_total = track_params["first_lap_incident_rate"] + track_params["mechanical_dnf_rate"]
    fl_frac = (track_params["first_lap_incident_rate"] / base_total) if base_total > 0 else 0.5
    if dnf_rates is None:
        dnf_rates = np.full(n, base_total)

    sc_model = SafetyCarModel(base_prob_per_lap=track_params["sc_prob_per_lap"])

    pace = predicted_positions.copy() + rng.normal(0, 0.5, n)
    order = np.argsort(pace).tolist()

    # Per-driver DNFs: one draw against that driver's rate, then decide whether it's
    # a first-lap incident or a mid-race mechanical failure.
    dnf_lap = {}
    for i in range(n):
        if rng.random() < dnf_rates[i]:
            dnf_lap[i] = 1 if rng.random() < fl_frac else int(rng.integers(2, total_laps))

    # Pit stop pace adjustment
    for i in range(n):
        if i not in dnf_lap:
            stops = rng.integers(1, max(2, int(track_params["avg_pit_stops"] + 1)))
            pit_delta = sum(rng.normal(0, 0.4) for _ in range(stops))
            pace[i] += pit_delta * 0.3

    # Safety cars
    sc_set = set(sc_model.simulate(total_laps, rng))

    # Lap-by-lap overtaking
    active = set(range(n)) - set(dnf_lap.keys())

    for lap in range(1, total_laps + 1):
        for driver_idx, dlap in dnf_lap.items():
            if dlap == lap:
                active.discard(driver_idx)

        if lap in sc_set or lap % 3 != 0:
            continue

        running = [d for d in order if d in active]
        for j in range(len(running) - 1):
            ahead = running[j]
            behind = running[j + 1]
            delta = pace[ahead] - pace[behind]

            if delta > 0.3 and rng.random() < min(0.15 * (delta / 0.3), 0.8):
                idx_a = order.index(ahead)
                idx_b = order.index(behind)
                order[idx_a], order[idx_b] = order[idx_b], order[idx_a]

    # Final positions
    running = [d for d in order if d in active]
    dnf_list = [d for d in order if d not in active]

    positions = np.zeros(n, dtype=int)
    for pos, driver_idx in enumerate(running, 1):
        positions[driver_idx] = pos
    for pos, driver_idx in enumerate(dnf_list, len(running) + 1):
        positions[driver_idx] = pos

    # Track DNF explicitly — a back-of-grid finish is NOT the same as a retirement.
    dnf_flags = np.zeros(n, dtype=bool)
    for i in dnf_lap:
        dnf_flags[i] = True

    return positions, dnf_flags


def run_simulation(predicted_order: pd.DataFrame, total_laps: int,
                   n_sims: int = NUM_SIMULATIONS, track_params: dict = None) -> dict:
    if track_params is None:
        track_params = DEFAULT_TRACK_PARAMS

    rng = np.random.default_rng(MC_RANDOM_SEED)

    drivers = predicted_order["Driver"].values
    predicted_positions = predicted_order["PredictedPosition"].values.astype(float)
    n_drivers = len(drivers)

    # Per-driver reliability (uses DNFRate_Last10 / TeamDNFRate_Last10 if present).
    dnf_rates = compute_dnf_rates(predicted_order, track_params)

    all_positions = np.zeros((n_sims, n_drivers), dtype=int)
    all_dnf = np.zeros((n_sims, n_drivers), dtype=bool)

    for i in range(n_sims):
        sim_rng = np.random.default_rng(rng.integers(0, 2**32))
        positions, dnf_flags = simulate_single_race(
            drivers, predicted_positions, total_laps, sim_rng, track_params, dnf_rates
        )
        all_positions[i] = positions
        all_dnf[i] = dnf_flags

    # Build summary stats
    position_counts = np.zeros((n_drivers, n_drivers + 1))
    for i in range(n_drivers):
        for pos in range(1, n_drivers + 1):
            position_counts[i][pos] = np.sum(all_positions[:, i] == pos)

    position_probs = position_counts / n_sims

    summary = []
    for i, driver in enumerate(drivers):
        positions = all_positions[:, i]
        expected_points = np.mean([POINTS_SYSTEM.get(p, 0) for p in positions])

        summary.append({
            "Driver": driver,
            "ExpectedPosition": round(np.mean(positions), 1),
            "MedianPosition": int(np.median(positions)),
            "StdPosition": round(np.std(positions), 2),
            "WinProb": round(position_probs[i][1] * 100, 1),
            "PodiumProb": round(sum(position_probs[i][1:4]) * 100, 1),
            "PointsProb": round(sum(position_probs[i][1:11]) * 100, 1),
            "DNFProb": round(all_dnf[:, i].mean() * 100, 1),   # now a real retirement rate
            "ExpectedPoints": round(expected_points, 2),
            "P5_Position": int(np.percentile(positions, 5)),
            "P95_Position": int(np.percentile(positions, 95)),
        })

    summary_df = pd.DataFrame(summary).sort_values("ExpectedPosition")
    position_probs_df = pd.DataFrame(
        position_probs, index=drivers,
        columns=[f"P{i}" for i in range(n_drivers + 1)]
    )

    return {
        "summary": summary_df,
        "position_probs": position_probs_df,
    }


# ---------------------------------------------------------------------------
# JSON export helpers — bridge between the offline pipeline and the frontend.
# ---------------------------------------------------------------------------

# Map raw DataFrame columns -> clean JSON keys.
# (% and [] are legal Python labels but awkward to use in JS, so rename them here.)
COLUMN_MAP = {
    "Driver":           "driver",
    "ExpectedPosition": "expected_position",
    "MedianPosition":   "median_position",
    "StdPosition":      "std_position",
    "WinProb":          "win_pct",
    "PodiumProb":       "podium_pct",
    "PointsProb":       "points_pct",
    "DNFProb":          "dnf_pct",
    "ExpectedPoints":   "expected_points",
    "P5_Position":      "p5_position",
    "P95_Position":     "p95_position",
}


def export_race(results_df, year, round_no, name, laps, out_dir, actuals_df=None, mode="official"):
    """Write one race's Monte Carlo summary into a per-year folder."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = results_df.rename(columns=COLUMN_MAP)
    if actuals_df is not None and "FinishPosition" in actuals_df.columns:
        actuals = actuals_df[["Driver", "FinishPosition"]].rename(
            columns={"Driver": "driver", "FinishPosition": "actual"}
        )
        df = df.merge(actuals, on="driver", how="left")
        df["actual"] = df["actual"].where(df["actual"].notna(), None)

    payload = {
        "year": year,
        "round": round_no,
        "name": name,
        "laps": laps,
        "mode": mode,
        "drivers": df.to_dict(orient="records"),
    }
    path = out_dir / f"round_{round_no}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=float)
    return path


def export_index(races, out_dir):
    """Write the race-selector index: races = [{'round': 1, 'name': '...'}, ...]."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "races.json", "w") as f:
        json.dump(races, f, indent=2)