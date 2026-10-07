# Calc track specific event probabilities (DNF, Safety car, etc) from historical data

import numpy as np
import pandas as pd
from backend.src.data.feature_engineering import normalize_dnf

# Position-change ratios understate how much harder passing is (Monaco still sees
# changes from DNFs and the start), so the MC's pass chance scales with ratio ** exponent.
# Backtests were flat across exponents 0-2 (the RF already explains most of the movement).
OVERTAKE_EXPONENT = 1.0
OVERTAKE_SHRINK_RACES = 3
DNF_SHRINK_RACES = 3

def calibrate_track_events(master_df: pd.DataFrame) -> pd.DataFrame:
    master_df = normalize_dnf(master_df)
    if master_df["DNF"].dtype == object:
        master_df["DNF"] = master_df["DNF"].map(
            {True: True, False: False, "True": True, "False": False}
        )

    races = master_df.groupby(["Year", "RoundNumber", "CircuitName"])

    # Overtaking difficulty: how far classified finishers end up from their grid slot
    finishers = master_df[~master_df["DNF"].astype(bool) & (master_df["GridPosition"] >= 1)]
    pos_change = ((finishers["FinishPosition"] - finishers["GridPosition"]).abs()
                  .groupby([finishers["Year"], finishers["RoundNumber"]]).mean())

    track_stats = []
    for (year, rnd, circuit), race_data in races:
        total_drivers = len(race_data)
        dnf_count = race_data["DNF"].astype(int).sum()
        total_laps = race_data["TotalRaceLaps"].iloc[0] if "TotalRaceLaps" in race_data.columns else 57
        avg_pit_stops = race_data["NumPitStops"].mean()
        avg_pos_change = pos_change.get((year, rnd), np.nan)

        track_stats.append({
            "CircuitName": circuit,
            "Year": year,
            "DNFRate": dnf_count / total_drivers,
            "TotalLaps": total_laps,
            "AvgPitStops": avg_pit_stops,
            "AvgPosChange": avg_pos_change,
        })

    stats_df = pd.DataFrame(track_stats)
    global_avg_dnf = stats_df["DNFRate"].mean()

    calibrated = stats_df.groupby("CircuitName").agg(
        AvgDNFRate=("DNFRate", "mean"),
        AvgTotalLaps=("TotalLaps", "mean"),
        AvgPitStops=("AvgPitStops", "mean"),
        AvgPosChange=("AvgPosChange", "mean"),
        RaceCount=("Year", "count"),
    ).reset_index()

    # >1 = more position changes than an average track. Shrunk toward 1 for circuits
    # with few races so one chaotic wet race doesn't define a track.
    ratio = (calibrated["AvgPosChange"] / stats_df["AvgPosChange"].mean()).fillna(1.0)
    weight = calibrated["RaceCount"] / (calibrated["RaceCount"] + OVERTAKE_SHRINK_RACES)
    calibrated["OvertakeRatio"] = 1.0 + (ratio - 1.0) * weight

    # Track DNF rate = the circuit's real historical rate, shrunk toward the global rate
    # for circuits with few races. The MC blends this with each driver's/team's own
    # rate, so it should sit on the same (real) scale. ~40% of DNFs happen on lap 1.
    weight = calibrated["RaceCount"] / (calibrated["RaceCount"] + DNF_SHRINK_RACES)
    calibrated["TotalMCRate"] = weight * calibrated["AvgDNFRate"] + (1 - weight) * global_avg_dnf
    calibrated["FirstLapIncidentRate"] = (calibrated["TotalMCRate"] * 0.4).clip(0.01, 0.15)
    calibrated["MechanicalDNFRate"] = (calibrated["TotalMCRate"] * 0.6).clip(0.01, 0.20)

    # SC rate: proportional to DNF rate, scaled around our default of 0.015
    calibrated["SCProbPerLap"] = 0.015

    return calibrated
    
# Get calibrated parameters for a specific circuit.
    # Falls back to global averages if circuit not found.
def get_track_params(calibrated_df: pd.DataFrame, circuit_name: str) -> dict:
    match = calibrated_df[calibrated_df["CircuitName"] == circuit_name]

    if match.empty:
        # Global fallback
        return {
            "sc_prob_per_lap": calibrated_df["SCProbPerLap"].mean(),
            "first_lap_incident_rate": calibrated_df["FirstLapIncidentRate"].mean(),
            "mechanical_dnf_rate": calibrated_df["MechanicalDNFRate"].mean(),
            "avg_pit_stops": calibrated_df["AvgPitStops"].mean(),
            "overtake_factor": 1.0,
            "total_laps": 57,
        }

    row = match.iloc[0]
    return {
        "sc_prob_per_lap": row["SCProbPerLap"],
        "first_lap_incident_rate": row["FirstLapIncidentRate"],
        "mechanical_dnf_rate": row["MechanicalDNFRate"],
        "avg_pit_stops": row["AvgPitStops"],
        # Older pickled calibrations (live state blobs) predate OvertakeRatio
        "overtake_factor": float(row.get("OvertakeRatio", 1.0)) ** OVERTAKE_EXPONENT,
        "total_laps": int(row["AvgTotalLaps"]),
    }