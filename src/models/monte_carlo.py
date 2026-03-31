# Core Monte Carlo simulation engine (optimized).

import numpy as np
import pandas as pd
from config import NUM_SIMULATIONS, MC_RANDOM_SEED, POINTS_SYSTEM
from src.models.race_events import SafetyCarModel


def simulate_single_race(drivers: np.ndarray, predicted_positions: np.ndarray,
                         total_laps: int, rng: np.random.Generator,
                         track_params: dict = None) -> np.ndarray:
    n = len(drivers)

    # Use track-specific params or defaults
    if track_params is None:
        track_params = {
            "sc_prob_per_lap": 0.015,
            "first_lap_incident_rate": 0.04,
            "mechanical_dnf_rate": 0.02,
            "avg_pit_stops": 2.0,
        }

    sc_model = SafetyCarModel(base_prob_per_lap=track_params["sc_prob_per_lap"])

    pace = predicted_positions.copy() + rng.normal(0, 0.5, n)
    order = np.argsort(pace).tolist()

    # DNFs using track-calibrated rates
    dnf_lap = {}
    for i in range(n):
        if rng.random() < track_params["first_lap_incident_rate"]:
            dnf_lap[i] = 1
        elif rng.random() < track_params["mechanical_dnf_rate"]:
            dnf_lap[i] = int(rng.integers(2, total_laps))

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

    return positions


def run_simulation(predicted_order: pd.DataFrame, total_laps: int,
                   n_sims: int = NUM_SIMULATIONS, track_params: dict = None) -> dict:
    rng = np.random.default_rng(MC_RANDOM_SEED)

    drivers = predicted_order["Driver"].values
    predicted_positions = predicted_order["PredictedPosition"].values.astype(float)
    n_drivers = len(drivers)

    all_positions = np.zeros((n_sims, n_drivers), dtype=int)

    for i in range(n_sims):
        sim_rng = np.random.default_rng(rng.integers(0, 2**32))
        all_positions[i] = simulate_single_race(
            drivers, predicted_positions, total_laps, sim_rng, track_params
        )

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
            "DNFProb": round(np.mean(positions > n_drivers) * 100, 1),
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