# Pull and cache F1 data via FastF1

import fastf1
import pandas as pd
from tqdm import tqdm
from config import SEASONS, CACHE_DIR

fastf1.Cache.enable_cache(CACHE_DIR)

def load_race_session(year: int, round_number: int) -> fastf1.core.Session:
    # Load a single race session with all data
    session = fastf1.get_session(year, round_number, "R")
    session.load(weather = True, telemetry = False, messages = True)
    return session

def extract_race_data(session: fastf1.core.Session) -> pd.DataFrame:
    # Extract data from a loaded race sesssion
        # Returns one row per driver
    laps = session.laps
    results = session.results
    weather = session.weather_data

    race_df = results[["Abbreviation", "GridPosition", "Position", "Points", "Status", "TeamName"]].copy()
    race_df.columns = ["Driver", "GridPosition", "FinishPosition", "Points", "Status", "Team"]

    # Track lap stats by driver
        # average laptime, best lap time, num laps, num pitstops
    lap_stats = (
        laps.groupby("Driver").agg(
            AvgLapTime=("LapTime", lambda x: x.dt.total_seconds().mean()),
            BestLapTime=("LapTime", lambda x: x.dt.total_seconds().min()),
            NumLaps=("LapNumber", "max"),
            NumPitStops=("PitInTime", lambda x: x.notna().sum()),
        ).reset_index()
    )

    tire_strats = (
        laps.groupby("Driver")["Compound"]
        .apply(lambda x: list(x.dropna().unique()))
        .reset_index()
        .rename(columns = {"Compound": "TireCompunds"})
    )

    weather_summary = {
        "AvgAirTemp": weather["AirTemp"].mean(),
        "AvgTrackTemp": weather["TrackTemp"].mean(),
        "AvgHumidity": weather["Humidity"].mean(),
        "AvgWindSpeed": weather["WindSpeed"].mean(),
        "Rainfall": weather["Rainfall"].any(),
    }

    race_df = race_df.merge(lap_stats, on="Driver", how="left")
    race_df = race_df.merge(tire_strats, on="Driver", how="left")

    for col, val in weather_summary.items():
        race_df[col] = val

    race_df["Year"] = session.event["EventDate"].year
    race_df["RoundNumber"] = session.event["RoundNumber"]
    race_df["CircuitName"] = session.event["EventName"]
    race_df["TotalRaceLaps"] = session.total_laps

    race_df["DNF"] = ~race_df["Status"].isin(["Finished", "+1 Lap", "+2 Laps", "+3 Laps"])

    return race_df

 # Pull every race from every season in SEASONS.
        #Returns a master DataFrame: one row per driver per race.
def build_master_dataset() -> pd.DataFrame:
    
    all_races = []

    for year in SEASONS:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        race_rounds = schedule[schedule["EventFormat"] != "testing"]["RoundNumber"].tolist()

        print(f"\n{'='*50}")
        print(f"Season {year}: {len(race_rounds)} races")
        print(f"{'='*50}")

        for rnd in tqdm(race_rounds, desc=f"{year}"):
            try:
                session = load_race_session(year, rnd)
                race_data = extract_race_data(session)
                all_races.append(race_data)
            except Exception as e:
                print(f"  Skipping {year} Round {rnd}: {e}")
                continue

    master_df = pd.concat(all_races, ignore_index=True)
    print(f"\nMaster dataset: {len(master_df)} rows, {master_df['Year'].nunique()} seasons, "
          f"{master_df['CircuitName'].nunique()} circuits")

    return master_df