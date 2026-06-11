# Pull and cache F1 data via FastF1

import fastf1 
import pandas as pd 
from tqdm import tqdm 
from backend.config import BASE_DIR, SEASONS, CACHE_DIR
import os

fastf1.Cache.enable_cache(CACHE_DIR)

def load_race_session(year: int, round_number: int) -> fastf1.core.Session:
    # Load a single race session with all data
    race = fastf1.get_session(year, round_number, "R")
    race.load(weather=True, telemetry=False, messages=True)

    try:
        quali = fastf1.get_session(year, round_number, "Q")
        quali.load(telemetry=False)
    except Exception:
        quali = None

    return race, quali


def load_practice_sessions(year: int, round_number: int) -> list:
    """Load all available practice sessions (FP1/FP2/FP3, or just FP1 on sprints).
    Returns a list of loaded sessions; missing ones are skipped, so it works
    for both conventional and sprint weekends without special-casing."""
    sessions = []
    for ident in ["FP1", "FP2", "FP3"]:
        try:
            fp = fastf1.get_session(year, round_number, ident)
            fp.load(telemetry=False, weather=False, messages=False)
            if fp.laps is not None and len(fp.laps) > 0:
                sessions.append(fp)
        except Exception:
            continue   # session doesn't exist (sprint weekend) or no data — fine
    return sessions


def extract_race_data(session, quali=None) -> pd.DataFrame:
    laps = session.laps
    results = session.results
    weather = session.weather_data

    race_df = results[["Abbreviation", "GridPosition", "Position",
                        "Points", "Status", "TeamName"]].copy()
    race_df.columns = ["Driver", "GridPosition", "FinishPosition",
                        "Points", "Status", "Team"]

    lap_stats = (
        laps.groupby("Driver")
        .agg(
            AvgLapTime=("LapTime", lambda x: x.dt.total_seconds().mean()),
            BestLapTime=("LapTime", lambda x: x.dt.total_seconds().min()),
            NumLaps=("LapNumber", "max"),
            NumPitStops=("PitInTime", lambda x: x.notna().sum()),
        ).reset_index()
    )

    tire_strats = (
        laps.groupby("Driver")["Compound"].apply(lambda x: list(x.dropna().unique())).reset_index().rename(columns={"Compound": "TireCompounds"})
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

    if quali is not None:
        quali_data = extract_quali_data(quali)
        if not quali_data.empty:
            race_df = race_df.merge(quali_data, on="Driver", how="left")

    for col, val in weather_summary.items():
        race_df[col] = val

    race_df["Year"] = session.event["EventDate"].year
    race_df["RoundNumber"] = session.event["RoundNumber"]
    race_df["CircuitName"] = session.event["EventName"]
    race_df["TotalRaceLaps"] = session.total_laps

    race_df["DNF"] = ~race_df["Status"].isin(["Finished", "+1 Lap", "+2 Laps", "+3 Laps"])

    return race_df

# extract qualifying pace gap data
def extract_quali_data(quali) -> pd.DataFrame:
    if quali is None:
        return pd.DataFrame()

    laps = quali.laps
    best_laps = (
        laps.groupby("Driver")["LapTime"].min().dt.total_seconds().reset_index().rename(columns={"LapTime": "QualiBestTime"})
    )

    pole_time = best_laps["QualiBestTime"].min()
    best_laps["QualiGapToPole"] = best_laps["QualiBestTime"] - pole_time
    best_laps["QualiGapPct"] = (best_laps["QualiGapToPole"] / pole_time) * 100

    return best_laps


def _clean_long_run_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Keep only representative green-flag long-run laps.
    Removes in/out laps, non-green laps, and per-driver time outliers so the
    average reflects true race pace, not quali sims or traffic-compromised laps."""
    df = laps.copy()
    df = df[df["LapTime"].notna()]
    # Drop in-laps and out-laps (pit involvement distorts the time).
    if "PitInTime" in df.columns and "PitOutTime" in df.columns:
        df = df[df["PitInTime"].isna() & df["PitOutTime"].isna()]
    # Green-flag only, if track status is available ("1" == all clear).
    if "TrackStatus" in df.columns:
        df = df[df["TrackStatus"].astype(str) == "1"]
    if df.empty:
        return df
    df["LapSeconds"] = df["LapTime"].dt.total_seconds()
    # Remove obvious outliers per driver (aborted/slow laps) via IQR.
    cleaned = []
    for drv, g in df.groupby("Driver"):
        if len(g) < 3:
            continue
        q1, q3 = g["LapSeconds"].quantile([0.25, 0.75])
        iqr = q3 - q1
        keep = g[(g["LapSeconds"] >= q1 - 1.5 * iqr) & (g["LapSeconds"] <= q3 + 1.5 * iqr)]
        cleaned.append(keep)
    return pd.concat(cleaned, ignore_index=True) if cleaned else df.iloc[0:0]


def extract_practice_pace(year: int, round_number: int) -> pd.DataFrame:
    """One row per driver: long-run practice pace + gap to fastest + teammate delta.
    Empty frame if no practice data (so callers merge with how='left' and get NaN)."""
    empty = pd.DataFrame(columns=["Driver", "PracticePace", "PracticePaceGap",
                                  "PracticePaceVsTeammate"])
    sessions = load_practice_sessions(year, round_number)
    if not sessions:
        return empty

    all_laps = pd.concat([s.laps for s in sessions], ignore_index=True)
    clean = _clean_long_run_laps(all_laps)
    if clean.empty:
        return empty

    # Trimmed mean of clean long-run laps = race-representative pace.
    pace = (clean.groupby("Driver")["LapSeconds"]
            .apply(lambda x: x.sort_values().iloc[: max(3, int(len(x) * 0.7))].mean())
            .reset_index().rename(columns={"LapSeconds": "PracticePace"}))

    # Gap to the fastest driver's practice pace (track-relative, comparable across races).
    pace["PracticePaceGap"] = pace["PracticePace"] - pace["PracticePace"].min()

    # Teammate delta: needs team mapping. Pull it from the laps' Team column.
    if "Team" in all_laps.columns:
        team_map = (all_laps.dropna(subset=["Team"])
                    .groupby("Driver")["Team"].first().reset_index())
        pace = pace.merge(team_map, on="Driver", how="left")
        team_best = pace.groupby("Team")["PracticePace"].transform("min")
        pace["PracticePaceVsTeammate"] = pace["PracticePace"] - team_best
        pace = pace.drop(columns=["Team"])
    else:
        pace["PracticePaceVsTeammate"] = pd.NA

    return pace


#Pull every race from every season in SEASONS.
    # Saves per-season CSVs so progress isn't lost on rate limit errors.
def build_master_dataset() -> pd.DataFrame:
    
    all_races = []
    save_dir = os.path.join(BASE_DIR, "data", "processed", "seasons")
    os.makedirs(save_dir, exist_ok=True)

    for year in SEASONS:
        season_path = os.path.join(save_dir, f"season_{year}.csv")

        # Skip if we already have this season
        if os.path.exists(season_path):
            print(f"Loading cached {year}")
            all_races.append(pd.read_csv(season_path))
            continue

        schedule = fastf1.get_event_schedule(year, include_testing=False)
        race_rounds = schedule[schedule["EventFormat"] != "testing"]["RoundNumber"].tolist()

        print(f"\n{'='*50}")
        print(f"Season {year}: {len(race_rounds)} races")
        print(f"{'='*50}")

        season_races = []
        for rnd in tqdm(race_rounds, desc=f"{year}"):
            try:
                race, quali = load_race_session(year, rnd)
                race_data = extract_race_data(race, quali)
                practice = extract_practice_pace(year, rnd)
                if not practice.empty:
                    race_data = race_data.merge(practice, on="Driver", how="left")
                season_races.append(race_data)
            except Exception as e:
                print(f"  Skipping {year} Round {rnd}: {e}")
                continue

        if season_races:
            season_df = pd.concat(season_races, ignore_index=True)
            season_df.to_csv(season_path, index=False)
            all_races.append(season_df)
            print(f"Saved {year} ({len(season_df)} rows)")

    master_df = pd.concat(all_races, ignore_index=True)
    print(f"\nMaster dataset: {len(master_df)} rows, {master_df['Year'].nunique()} seasons, "
          f"{master_df['CircuitName'].nunique()} circuits")

    return master_df
