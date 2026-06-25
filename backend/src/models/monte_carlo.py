# Core Monte Carlo simulation engine.

import numpy as np
import pandas as pd
import json
from pathlib import Path
from backend.config import NUM_SIMULATIONS, MC_RANDOM_SEED, POINTS_SYSTEM


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
    drv  = df["DNFRate_Last10"].to_numpy()  if "DNFRate_Last10"  in df.columns else np.full(n, base)
    team = df["TeamDNFRate_Last10"].to_numpy() if "TeamDNFRate_Last10" in df.columns else np.full(n, base)
    drv  = np.nan_to_num(drv,  nan=base)
    team = np.nan_to_num(team, nan=base)
    rate = weights[0] * base + weights[1] * drv + weights[2] * team
    return np.clip(rate, lo, hi)


def run_simulation(predicted_order: pd.DataFrame, total_laps: int,
                   n_sims: int = NUM_SIMULATIONS, track_params: dict = None,
                   seed: "int | None" = MC_RANDOM_SEED) -> dict:
    """Run n_sims Monte Carlo races and return aggregate probabilities.

    seed=None  → fresh random results every call (live per-user predictions).
    seed=int   → reproducible results (offline JSON exports).
    """
    if track_params is None:
        track_params = DEFAULT_TRACK_PARAMS

    rng = np.random.default_rng(seed)

    drivers             = predicted_order["Driver"].values
    predicted_positions = predicted_order["PredictedPosition"].values.astype(float)
    n                   = len(drivers)
    dnf_rates           = compute_dnf_rates(predicted_order, track_params)

    base_total = (track_params["first_lap_incident_rate"] +
                  track_params["mechanical_dnf_rate"])
    fl_frac    = (track_params["first_lap_incident_rate"] / base_total
                  if base_total > 0 else 0.5)
    max_stops  = max(2, int(track_params["avg_pit_stops"] + 1))
    sc_base    = track_params["sc_prob_per_lap"]
    max_pairs  = max(1, n - 1)
    ot_laps    = max(1, total_laps // 3)

    # ── Pre-generate ALL random numbers at once ───────────────────────────────
    # Replaces 20 000 RNG object creations and thousands of individual small calls
    # with a handful of fast bulk numpy operations.
    pace_noise     = rng.normal(0, 0.5, (n_sims, n))
    dnf_rolls      = rng.random((n_sims, n))
    fl_rolls       = rng.random((n_sims, n))
    dnf_lap_mid    = rng.integers(2, max(3, total_laps), (n_sims, n))
    pit_counts     = rng.integers(1, max_stops, (n_sims, n))
    pit_noise      = rng.normal(0, 0.4, (n_sims, n, max_stops))
    sc_rolls       = rng.random((n_sims, total_laps))
    overtake_rolls = rng.random((n_sims, ot_laps, max_pairs))

    # SC probability per lap (first 3 laps are 4× riskier)
    sc_probs = np.full(total_laps, sc_base)
    sc_probs[:min(3, total_laps)] *= 4.0

    # Vectorised DNF decisions (avoids per-sim per-driver Python conditionals)
    driver_dnfs    = dnf_rolls < dnf_rates[np.newaxis, :]         # (n_sims, n) bool
    dnf_lap_matrix = np.where(fl_rolls < fl_frac, 1, dnf_lap_mid) # (n_sims, n) int

    # ── Simulation loop ───────────────────────────────────────────────────────
    all_positions = np.zeros((n_sims, n), dtype=np.int32)
    all_dnf_flags = np.zeros((n_sims, n), dtype=bool)

    for sim_i in range(n_sims):
        pace = predicted_positions + pace_noise[sim_i]

        # Per-sim DNF lap map
        dnf_lap = {}
        for d in range(n):
            if driver_dnfs[sim_i, d]:
                dnf_lap[d] = int(dnf_lap_matrix[sim_i, d])

        # Pit-stop pace adjustments
        for d in range(n):
            if d not in dnf_lap:
                stops = int(pit_counts[sim_i, d])
                for s in range(stops):
                    pace[d] += pit_noise[sim_i, d, s] * 0.3

        # Safety car laps — cooldown makes this inherently sequential,
        # but random draws are already pre-generated above.
        sc_set   = set()
        cooldown = 0
        for lap_i in range(total_laps):
            if cooldown > 0:
                cooldown -= 1
                continue
            if sc_rolls[sim_i, lap_i] < sc_probs[lap_i]:
                sc_set.add(lap_i + 1)
                cooldown = 4

        # Initial order by pace; rank[] gives O(1) position lookups so
        # overtake swaps no longer require the O(n) order.index() scan.
        order = np.argsort(pace).tolist()
        rank  = [0] * n
        for pos_i, d in enumerate(order):
            rank[d] = pos_i

        active  = set(range(n))
        ot_lp_i = 0

        for lap in range(1, total_laps + 1):
            for d, dlap in dnf_lap.items():
                if dlap == lap:
                    active.discard(d)

            if lap in sc_set or lap % 3 != 0:
                continue

            running  = [d for d in order if d in active]
            roll_row = overtake_rolls[sim_i, min(ot_lp_i, ot_laps - 1)]

            for j in range(len(running) - 1):
                ahead  = running[j]
                behind = running[j + 1]
                delta  = pace[ahead] - pace[behind]
                if delta > 0.3 and roll_row[min(j, max_pairs - 1)] < min(0.15 * delta / 0.3, 0.8):
                    ra, rb = rank[ahead], rank[behind]
                    order[ra], order[rb] = order[rb], order[ra]
                    rank[ahead], rank[behind] = rb, ra

            ot_lp_i += 1

        # Assign final positions
        running_final = [d for d in order if d in active]
        dnf_list      = [d for d in order if d not in active]
        positions = np.empty(n, dtype=np.int32)
        for pos_i, d in enumerate(running_final, 1):
            positions[d] = pos_i
        for pos_i, d in enumerate(dnf_list, len(running_final) + 1):
            positions[d] = pos_i

        all_positions[sim_i] = positions
        for d in dnf_lap:
            all_dnf_flags[sim_i, d] = True

    # ── Vectorised aggregation ─────────────────────────────────────────────────
    # np.bincount replaces the O(n²) Python double-loop
    position_counts = np.zeros((n, n + 1))
    for i in range(n):
        position_counts[i] = np.bincount(all_positions[:, i], minlength=n + 1)
    position_probs = position_counts / n_sims

    # Array-index lookup replaces 20 000 × n dict.get() calls
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
            "MedianPosition":   int(np.median(col)),
            "StdPosition":      round(float(np.std(col)), 2),
            "WinProb":          round(pr[1] * 100, 1),
            "PodiumProb":       round(float(np.sum(pr[1:4])) * 100, 1),
            "PointsProb":       round(float(np.sum(pr[1:11])) * 100, 1),
            "DNFProb":          round(float(all_dnf_flags[:, i].mean()) * 100, 1),
            "ExpectedPoints":   round(float(np.mean(points_arr[col])), 2),
            "P5_Position":      int(np.percentile(col, 5)),
            "P95_Position":     int(np.percentile(col, 95)),
        })

    summary_df = pd.DataFrame(summary).sort_values("ExpectedPosition")
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
