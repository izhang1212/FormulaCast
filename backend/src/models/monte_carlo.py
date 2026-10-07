# Core Monte Carlo simulation engine.
#
# The Random Forest gives each driver a PredictedPosition: where they should finish on
# average. The Monte Carlo turns that into a distribution by racing the field lap by lap:
#   1. Each driver gets a race pace = PredictedPosition + day-of-race noise (lower = faster).
#   2. Cars start in grid order, not pace order, so the race has to sort them out.
#   3. Every lap, adjacent cars can swap. A faster car behind passes with a probability that
#      grows with the pace gap and the track's overtaking factor (Monaco low, Las Vegas high).
#   4. Lap 1 and safety car restarts shuffle the order regardless of pace; laps under the
#      safety car allow no passing. Spins/slow stops drop a car a few places mid-race.
#   5. Retirements fall out of the running order and are classified by laps completed.
# All simulations run at once as (n_sims, n_drivers) arrays; only the lap loop is sequential.

import numpy as np
import pandas as pd
import json
from pathlib import Path
from backend.config import NUM_SIMULATIONS, MC_RANDOM_SEED, POINTS_SYSTEM


DEFAULT_TRACK_PARAMS = {
    "sc_prob_per_lap": 0.015,
    "first_lap_incident_rate": 0.06,
    "mechanical_dnf_rate": 0.09,
    "avg_pit_stops": 2.0,
    "overtake_factor": 1.0,
}

# Race dynamics, tuned to minimise ranked probability score on walk-forward backtests
# (tuned on 2019-2023, checked on 2024-2026). Units are finishing positions, the same
# scale as the Random Forest's PredictedPosition.
SIM_PARAMS = {
    "pace_noise_sd":      2.5,    # day-of-race form/strategy noise on an average driver's pace
    "pace_noise_power":   0.5,    # noise scales with (PredictedPosition / field mean) ** power,
                                  # so front-runners are more predictable than the midfield
    "overtake_max_prob":  0.3,    # per-lap pass chance for a much faster car (avg track)
    "overtake_scale":     1.0,    # pace gap at which a pass reaches ~63% of the max chance
    "start_chaos":        0.10,   # lap-1 chance each adjacent pair swaps regardless of pace
    "restart_chaos":      0.05,   # same, on the lap a safety car period ends
    "sc_duration":        4,      # laps per safety car period
    "incident_rate":      0.25,   # spins / slow stops / penalties per driver per race
    "incident_max_drop":  4,      # an incident costs 1..this many places
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
    drv  = df["DNFRate_Last10"].to_numpy()  if "DNFRate_Last10"  in df.columns else np.full(n, base)
    team = df["TeamDNFRate_Last10"].to_numpy() if "TeamDNFRate_Last10" in df.columns else np.full(n, base)
    drv  = np.nan_to_num(drv,  nan=base)
    team = np.nan_to_num(team, nan=base)
    rate = weights[0] * base + weights[1] * drv + weights[2] * team
    return np.clip(rate, lo, hi)


def median_position(probs: np.ndarray) -> int:
    """Median finish from a P0..Pn probability row: the first position with >= 50% of
    outcomes at or ahead of it. It's the headline prediction because it minimises
    absolute error; the mean gets dragged toward the back by the ~15% DNF tail."""
    return int(np.searchsorted(np.cumsum(probs), 0.5 - 1e-9))


def sort_by_prediction(summary: pd.DataFrame) -> pd.DataFrame:
    """Predicted finishing order: median position, ties broken by expected position."""
    return summary.sort_values(["MedianPosition", "ExpectedPosition"])


def starting_order(df: pd.DataFrame) -> np.ndarray:
    """Driver indices in grid order. Pit-lane starts (grid 0) and missing grid slots go
    to the back; ties and a missing GridPosition column fall back to PredictedPosition."""
    pred = df["PredictedPosition"].to_numpy(dtype=float)
    if "GridPosition" not in df.columns:
        return np.argsort(pred, kind="stable")
    grid = pd.to_numeric(df["GridPosition"], errors="coerce").to_numpy(dtype=float)
    grid = np.where(np.isnan(grid) | (grid < 1), 1000.0, grid)
    return np.lexsort((pred, grid))


def _safety_car_laps(rng, n_sims, total_laps, sc_probs, duration):
    """(n_sims, total_laps + 2) bool arrays indexed by lap: under SC, and restart laps."""
    under = np.zeros((n_sims, total_laps + 2), dtype=bool)
    restart = np.zeros_like(under)
    remaining = np.zeros(n_sims, dtype=np.int32)
    rolls = rng.random((n_sims, total_laps + 1))
    for lap in range(1, total_laps + 1):
        active = remaining > 0
        under[:, lap] = active
        remaining[active] -= 1
        restart[active & (remaining == 0), lap + 1] = True
        deploy = ~active & (rolls[:, lap] < sc_probs[lap])
        under[deploy, lap] = True
        remaining[deploy] = duration - 1
        restart[deploy & (remaining == 0), lap + 1] = True
    return under, restart


def _swap_pass(order, pace, running, rng, parity, base_prob, scale, chaos):
    """One round of adjacent-pair passing on pairs (parity, parity+1), (parity+2, ...).
    Odd/even alternation means no car is in two pairs in the same round."""
    n = order.shape[1]
    ks = np.arange(parity, n - 1, 2)
    if len(ks) == 0:
        return
    rows = np.arange(order.shape[0])[:, None]
    ahead, behind = order[:, ks], order[:, ks + 1]
    gap = pace[rows, ahead] - pace[rows, behind]          # > 0 → car behind is faster
    p = base_prob * (1.0 - np.exp(-np.maximum(gap, 0.0) / scale))
    p = chaos + (1.0 - chaos) * p
    swap = running[rows, behind] & (rng.random(ahead.shape) < p)
    order[:, ks] = np.where(swap, behind, ahead)
    order[:, ks + 1] = np.where(swap, ahead, behind)


def _reorder(order, keys_by_driver):
    """Stable re-sort of each simulation's running order by a per-driver key."""
    keys = np.take_along_axis(keys_by_driver, order, axis=1)
    idx = np.argsort(keys, axis=1, kind="stable")
    return np.take_along_axis(order, idx, axis=1)


def run_simulation(predicted_order: pd.DataFrame, total_laps: int,
                   n_sims: int = NUM_SIMULATIONS, track_params: dict = None,
                   seed: "int | None" = MC_RANDOM_SEED, sim_params: dict = None) -> dict:
    """Run n_sims Monte Carlo races and return aggregate probabilities.

    predicted_order needs Driver and PredictedPosition; GridPosition (start order) and
    DNFRate_Last10 / TeamDNFRate_Last10 (reliability) are used when present.

    seed=None  → fresh random results every call (live per-user predictions).
    seed=int   → reproducible results (offline JSON exports).
    """
    tp = {**DEFAULT_TRACK_PARAMS, **(track_params or {})}
    sp = {**SIM_PARAMS, **(sim_params or {})}
    rng = np.random.default_rng(seed)

    drivers   = predicted_order["Driver"].values
    predicted = predicted_order["PredictedPosition"].to_numpy(dtype=float)
    n         = len(drivers)
    laps      = max(2, int(total_laps))
    rows      = np.arange(n_sims)[:, None]

    # Race pace for each simulated race (lower = faster)
    noise_sd = sp["pace_noise_sd"] * (np.clip(predicted, 1, None) / np.clip(predicted, 1, None).mean()) ** sp["pace_noise_power"]
    pace = predicted[np.newaxis, :] + rng.normal(0, 1, (n_sims, n)) * noise_sd[np.newaxis, :]

    # Retirements: who, and on which lap (laps + 1 = finishes the race)
    dnf_rates  = compute_dnf_rates(predicted_order, tp)
    base_total = tp["first_lap_incident_rate"] + tp["mechanical_dnf_rate"]
    fl_frac    = tp["first_lap_incident_rate"] / base_total if base_total > 0 else 0.5
    retires    = rng.random((n_sims, n)) < dnf_rates[np.newaxis, :]
    retire_lap = np.where(rng.random((n_sims, n)) < fl_frac, 1,
                          rng.integers(2, laps + 1, (n_sims, n)))
    retire_lap = np.where(retires, retire_lap, laps + 1)

    # Safety car: per-lap deployment chance, first 3 laps 4× riskier
    sc_probs = np.full(laps + 1, tp["sc_prob_per_lap"])
    sc_probs[1:4] *= 4.0
    under_sc, restart = _safety_car_laps(rng, n_sims, laps, sc_probs, sp["sc_duration"])

    pass_prob     = min(sp["overtake_max_prob"] * tp.get("overtake_factor", 1.0), 0.95)
    incident_prob = sp["incident_rate"] / laps
    scale         = sp["overtake_scale"]
    order = np.tile(starting_order(predicted_order), (n_sims, 1))

    for lap in range(1, laps + 1):
        running = retire_lap > lap

        # Retired cars drop behind every running car; later retirements classify ahead.
        if (retire_lap == lap).any():
            pos = np.empty_like(order)
            pos[rows, order] = np.arange(n)
            keys = np.where(running, pos, n * (1 + laps - retire_lap) + pos)
            order = _reorder(order, keys)

        green = ~under_sc[:, lap]

        # Mid-race incidents (spin, slow stop, penalty): lose 1..max_drop places
        if lap > 1 and incident_prob > 0:
            hit = running & green[:, None] & (rng.random((n_sims, n)) < incident_prob)
            if hit.any():
                pos = np.empty_like(order)
                pos[rows, order] = np.arange(n)
                drop = rng.integers(1, sp["incident_max_drop"] + 1, (n_sims, n))
                keys = np.where(hit, np.minimum(pos + drop + 0.5, n - 0.5), pos)
                keys = np.where(running, keys, n * (1 + laps - retire_lap) + pos)
                order = _reorder(order, keys)

        if lap == 1:
            chaos = sp["start_chaos"]
        else:
            chaos = np.where(restart[:, lap], sp["restart_chaos"], 0.0)[:, None]
        base = np.where(green, pass_prob, 0.0)[:, None]
        if lap == 1:
            # The start: both pair parities, so every car can gain or lose a place
            _swap_pass(order, pace, running, rng, 0, base, scale, chaos)
            _swap_pass(order, pace, running, rng, 1, base, scale, chaos)
        else:
            _swap_pass(order, pace, running, rng, lap % 2, base, scale, chaos)

    all_positions = np.empty((n_sims, n), dtype=np.int32)
    all_positions[rows, order] = np.arange(1, n + 1)
    all_dnf_flags = retire_lap <= laps

    # ── Vectorised aggregation ─────────────────────────────────────────────────
    position_counts = np.zeros((n, n + 1))
    for i in range(n):
        position_counts[i] = np.bincount(all_positions[:, i], minlength=n + 1)
    position_probs = position_counts / n_sims

    points_arr = np.zeros(n + 1)
    for pos, pts in POINTS_SYSTEM.items():
        if pos <= n:
            points_arr[pos] = pts

    summary = []
    for i, driver in enumerate(drivers):
        col = all_positions[:, i]
        pr  = position_probs[i]
        summary.append({
            "Driver":           driver,
            "ExpectedPosition": round(float(np.mean(col)), 1),
            "MedianPosition":   median_position(pr),
            "StdPosition":      round(float(np.std(col)), 2),
            "WinProb":          round(pr[1] * 100, 1),
            "PodiumProb":       round(float(np.sum(pr[1:4])) * 100, 1),
            "PointsProb":       round(float(np.sum(pr[1:11])) * 100, 1),
            "DNFProb":          round(float(all_dnf_flags[:, i].mean()) * 100, 1),
            "ExpectedPoints":   round(float(np.mean(points_arr[col])), 2),
            "P5_Position":      int(np.percentile(col, 5)),
            "P95_Position":     int(np.percentile(col, 95)),
        })

    summary_df = sort_by_prediction(pd.DataFrame(summary))
    position_probs_df = pd.DataFrame(
        position_probs, index=drivers,
        columns=[f"P{i}" for i in range(n + 1)]
    )

    return {
        "summary":        summary_df,
        "position_probs": position_probs_df,
        "total_laps":     total_laps,
    }


# ---------------------------------------------------------------------------
# JSON export helpers — bridge between the offline pipeline and the frontend.
# ---------------------------------------------------------------------------

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
