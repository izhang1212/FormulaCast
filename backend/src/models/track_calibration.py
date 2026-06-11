# Calc track specific event probabilities (DNF, Safety car, etc) from historical data

import numpy as np
import pandas as pd

def calibrate_track_events(master_df: pd.DataFrame) -> pd.DataFrame:
    if master_df["DNF"].dtype == object:
        master_df["DNF"] = master_df["DNF"].map(
            {True: True, False: False, "True": True, "False": False}
        )

    races = master_df.groupby(["Year", "RoundNumber", "CircuitName"])

    track_stats = []
    for (year, rnd, circuit), race_data in races:
        total_drivers = len(race_data)
        dnf_count = race_data["DNF"].astype(int).sum()
        total_laps = race_data["TotalRaceLaps"].iloc[0] if "TotalRaceLaps" in race_data.columns else 57
        avg_pit_stops = race_data["NumPitStops"].mean()

        track_stats.append({
            "CircuitName": circuit,
            "Year": year,
            "DNFRate": dnf_count / total_drivers,
            "TotalLaps": total_laps,
            "AvgPitStops": avg_pit_stops,
        })

    stats_df = pd.DataFrame(track_stats)
    global_avg_dnf = stats_df["DNFRate"].mean()

    calibrated = stats_df.groupby("CircuitName").agg(
        AvgDNFRate=("DNFRate", "mean"),
        AvgTotalLaps=("TotalLaps", "mean"),
        AvgPitStops=("AvgPitStops", "mean"),
        RaceCount=("Year", "count"),
    ).reset_index()

    # Scale real DNF rates to match our effective MC rate of 0.06 total per driver
    # Our hardcoded defaults (0.04 + 0.02 = 0.06) work well on average
    # So scale each track's rate relative to the global average
    # Track with avg DNF rate gets 0.06, higher tracks get more, lower get less
    MC_TOTAL_RATE = 0.07
    scale = MC_TOTAL_RATE / global_avg_dnf

    calibrated["TotalMCRate"] = calibrated["AvgDNFRate"] * scale
    calibrated["FirstLapIncidentRate"] = (calibrated["TotalMCRate"] * 0.4).clip(0.01, 0.06)
    calibrated["MechanicalDNFRate"] = (calibrated["TotalMCRate"] * 0.6).clip(0.005, 0.03)

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
            "total_laps": 57,
        }

    row = match.iloc[0]
    return {
        "sc_prob_per_lap": row["SCProbPerLap"],
        "first_lap_incident_rate": row["FirstLapIncidentRate"],
        "mechanical_dnf_rate": row["MechanicalDNFRate"],
        "avg_pit_stops": row["AvgPitStops"],
        "total_laps": int(row["AvgTotalLaps"]),
    }