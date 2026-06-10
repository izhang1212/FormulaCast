"""
future_races.py — Assemble and store data for upcoming races so they can be predicted.

For a race that hasn't happened, FastF1 has NO session data (no results, telemetry,
weather, or entry list). What IS available is event/schedule metadata. So this stores:
  - metadata for the next N upcoming races (circuit, round, session datetimes)
  - the EXPECTED lineup, derived from the most recent completed race you've ingested
  - all race-day unknowns (grid, finish, weather, pace, quali) left as NaN, filled later
Stores the Qualifying datetime so the predictor can later switch between
'sample the grid' (pre-quali) and 'use the official grid' (post-quali).
Does NOT call session.load(), so it won't hit the session rate limit.
"""

import os
import glob
import re
import numpy as np
import pandas as pd
import fastf1
from config import CACHE_DIR

fastf1.Cache.enable_cache(CACHE_DIR)

SEASONS_DIR = os.path.join("data", "processed", "seasons")

# Columns present in your season CSVs that are UNKNOWN for a future race.
# Created and left NaN so the shape matches your historical rows exactly.
_UNKNOWN_COLS = [
    "GridPosition", "FinishPosition", "Points", "Status",
    "AvgLapTime", "BestLapTime", "NumLaps", "NumPitStops", "TireCompounds",
    "QualiBestTime", "QualiGapToPole", "QualiGapPct",
    "AvgAirTemp", "AvgTrackTemp", "AvgHumidity", "AvgWindSpeed", "Rainfall",
    "TotalRaceLaps", "DNF", "PracticePace", "PracticePaceGap", "PracticePaceVsTeammate",
]


def load_latest_season() -> pd.DataFrame:
    """Read the newest season_YYYY.csv you've pulled (used only for the lineup)."""
    files = glob.glob(os.path.join(SEASONS_DIR, "season_*.csv"))
    if not files:
        raise FileNotFoundError(f"No season files found in {SEASONS_DIR}")
    latest_file = max(files, key=lambda f: int(re.search(r"season_(\d{4})", f).group(1)))
    print(f"Reading lineup from {latest_file}")
    return pd.read_csv(latest_file)


def get_upcoming_events(n: int = 2) -> pd.DataFrame:
    """Metadata for the next `n` upcoming events of the current season."""
    remaining = fastf1.get_events_remaining(include_testing=False).head(n)
    rows = []
    for _, ev in remaining.iterrows():
        year = pd.Timestamp(ev["EventDate"]).year
        rnd = int(ev["RoundNumber"])
        event = fastf1.get_event(year, rnd)
        try:
            quali_dt = event.get_session_date("Q", utc=True)
        except TypeError:
            quali_dt = event.get_session_date("Q")   # older signature
        try:
            race_dt = event.get_session_date("R", utc=True)
        except TypeError:
            race_dt = event.get_session_date("R")
        rows.append({
            "Year": year,
            "RoundNumber": rnd,
            "CircuitName": ev["EventName"],   # matches your season CSV's CircuitName
            "Location": ev["Location"],
            "Country": ev["Country"],
            "EventFormat": ev["EventFormat"],
            "EventDate": pd.Timestamp(ev["EventDate"]),
            "QualifyingDateUtc": quali_dt,
            "RaceDateUtc": race_dt,
        })
    return pd.DataFrame(rows)


def get_expected_lineup(season_df: pd.DataFrame) -> pd.DataFrame:
    """Driver+Team roster from the most recent round in the newest season file."""
    latest_round = season_df["RoundNumber"].max()
    latest = season_df[season_df["RoundNumber"] == latest_round]
    lineup = latest[["Driver", "Team"]].drop_duplicates().reset_index(drop=True)
    print(f"Expected lineup: {len(lineup)} drivers from round {latest_round}")
    return lineup


def build_future_race_frame(n: int = 2) -> pd.DataFrame:
    """One row per (upcoming race x expected driver); known fields filled, unknowns NaN."""
    season_df = load_latest_season()
    lineup = get_expected_lineup(season_df)
    events = get_upcoming_events(n)

    frames = []
    for _, ev in events.iterrows():
        block = lineup.copy()
        for col in ["Year", "RoundNumber", "CircuitName", "Location", "Country",
                    "EventFormat", "EventDate", "QualifyingDateUtc", "RaceDateUtc"]:
            block[col] = ev[col]
        for col in _UNKNOWN_COLS:
            block[col] = np.nan
        frames.append(block)
    return pd.concat(frames, ignore_index=True)


def save_future_races(df, path=os.path.join("data", "processed", "future_races.csv")):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} rows ({df['CircuitName'].nunique()} races) -> {path}")


if __name__ == "__main__":
    future = build_future_race_frame(n=2)
    save_future_races(future)
    print(future[["CircuitName", "Driver", "Team",
                  "QualifyingDateUtc", "RaceDateUtc"]].to_string())