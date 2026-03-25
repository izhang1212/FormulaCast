# Monte Carlo simulation engine.


import numpy as np
import pandas as pd
from config import NUM_SIMULATIONS, MC_RANDOM_SEED, POINTS_SYSTEM
from src.race_events import SafetyCarModel, DNFModel, PitStopModel, OvertakeModel

 
# Simulate one race from predicted starting order.
    # Returns DataFrame with simulated finishing positions.
    
def simulate_single_race(
    predicted_order: pd.DataFrame, 
    total_laps: int,
    rng: np.random.Generator
) -> pd.DataFrame:

    sc_model = SafetyCarModel()
    dnf_model = DNFModel()
    pit_model = PitStopModel()
    overtake_model = OvertakeModel()

    result = predicted_order[["Driver", "PredictedPosition", "Team"]].copy()
    result = result.sort_values("PredictedPosition").reset_index(drop=True)

    drivers = result["Driver"].tolist()

    # Assign each driver a "pace" based on predicted position (lower = faster)
    result["Pace"] = result["PredictedPosition"] + rng.normal(0, 0.5, len(result))

    # DNFs
    team_reliability = {}
    if "TeamDNFRate_Last10" in predicted_order.columns:
        for _, row in predicted_order.iterrows():
            team_reliability[row["Driver"]] = max(row.get("TeamDNFRate_Last10", 0.03) / 0.03, 0.5)

    dnfs = dnf_model.simulate(drivers, team_reliability, rng)

    # Safety Car
    sc_laps = sc_model.simulate(total_laps, rng)

    # Pit Stops
    for i, row in result.iterrows():
        if row["Driver"] not in dnfs:
            num_stops = rng.integers(1, 4)
            pit_delta = sum(
                pit_model.simulate_stop(2.5, rng) - 2.5
                for _ in range(num_stops)
            )
            result.loc[i, "Pace"] += pit_delta * 0.3

    # Overtakes
    positions = result["Driver"].tolist()
    active_drivers = set(positions)

    for lap in range(1, total_laps + 1):
        # Remove any drivers who DNF on this lap
        for driver, dnf_lap in dnfs.items():
            if dnf_lap == lap and driver in active_drivers:
                active_drivers.discard(driver)

        # Safety car laps — no overtaking
        if lap in sc_laps:
            continue

        # Attempt overtakes between adjacent drivers
        running_order = [d for d in positions if d in active_drivers]
        for j in range(len(running_order) - 1):
            ahead = running_order[j]
            behind = running_order[j + 1]

            pace_ahead = result.loc[result["Driver"] == ahead, "Pace"].values[0]
            pace_behind = result.loc[result["Driver"] == behind, "Pace"].values[0]
            pace_delta = pace_ahead - pace_behind

            if overtake_model.attempt_overtake(pace_delta, rng):
                idx_a = positions.index(ahead)
                idx_b = positions.index(behind)
                positions[idx_a], positions[idx_b] = positions[idx_b], positions[idx_a]

    # Assign final positions
    running_order = [d for d in positions if d in active_drivers]
    dnf_list = [d for d in positions if d not in active_drivers]

    final = []
    for pos, driver in enumerate(running_order, 1):
        final.append({"Driver": driver, "FinalPosition": pos})
    for pos, driver in enumerate(dnf_list, len(running_order) + 1):
        final.append({"Driver": driver, "FinalPosition": pos})

    return pd.DataFrame(final)


#Run N Monte Carlo simulations.
    # Returns dict with probability distributions and summary stats.
def run_simulation(
    predicted_order: pd.DataFrame, 
    total_laps: int,
    n_sims: int = NUM_SIMULATIONS
) -> dict:
   
    rng = np.random.default_rng(MC_RANDOM_SEED)
    drivers = predicted_order["Driver"].tolist()
    n_drivers = len(drivers)

    # Position count matrix: drivers × positions
    position_counts = np.zeros((n_drivers, n_drivers + 1))

    all_results = []

    for i in range(n_sims):
        sim_rng = np.random.default_rng(rng.integers(0, 2**32))
        race_result = simulate_single_race(predicted_order, total_laps, sim_rng)

        for _, row in race_result.iterrows():
            driver_idx = drivers.index(row["Driver"])
            pos = int(row["FinalPosition"])
            if pos <= n_drivers:
                position_counts[driver_idx][pos] += 1

        all_results.append(race_result)

    # Summarize stats
    position_probs = position_counts / n_sims

    summary = []
    for i, driver in enumerate(drivers):
        driver_positions = []
        for res in all_results:
            pos = res.loc[res["Driver"] == driver, "FinalPosition"].values[0]
            driver_positions.append(pos)

        expected_points = sum(
            POINTS_SYSTEM.get(p, 0) for p in driver_positions
        ) / n_sims

        summary.append({
            "Driver": driver,
            "ExpectedPosition": round(np.mean(driver_positions), 1),
            "MedianPosition": int(np.median(driver_positions)),
            "StdPosition": round(np.std(driver_positions), 2),
            "WinProb": round(position_probs[i][1] * 100, 1),
            "PodiumProb": round(sum(position_probs[i][1:4]) * 100, 1),
            "PointsProb": round(sum(position_probs[i][1:11]) * 100, 1),
            "DNFProb": round(np.mean([p > n_drivers for p in driver_positions]) * 100, 1),
            "ExpectedPoints": round(expected_points, 2),
            "P5_Position": int(np.percentile(driver_positions, 5)),
            "P95_Position": int(np.percentile(driver_positions, 95)),
        })

    summary_df = pd.DataFrame(summary).sort_values("ExpectedPosition")
    position_probs_df = pd.DataFrame(position_probs, index=drivers,
                                      columns=[f"P{i}" for i in range(n_drivers + 1)])

    print("\n--- Monte Carlo Results ---")
    print(f"Simulations: {n_sims}")
    print(f"\n{'Driver':<8} {'E[Pos]':>7} {'Win%':>6} {'Podium%':>8} {'Points%':>8} {'E[Pts]':>7}")
    print("-" * 50)
    for _, row in summary_df.iterrows():
        print(f"{row['Driver']:<8} {row['ExpectedPosition']:>7.1f} {row['WinProb']:>5.1f}% "
              f"{row['PodiumProb']:>7.1f}% {row['PointsProb']:>7.1f}% {row['ExpectedPoints']:>7.2f}")

    return {
        "summary": summary_df,
        "position_probs": position_probs_df,
        "all_results": all_results,
    }