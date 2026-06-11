"""
update_seasons.py — Pull ONE season per run, first-needing-work first.

Past seasons: a saved file means done. The in-progress season (current year) is
re-pulled whenever completed rounds exist that aren't saved yet, so it stays fresh
as the season unfolds. Rate-limit cutoffs stop WITHOUT writing, so files stay
trustworthy; already-fetched rounds are cached and free to resume.

Now also pulls practice-pace features (long-run race pace from FP sessions) per
round, merged onto the race data. This adds up to 3 extra session loads per round,
so the cache and one-season-per-run cadence matter even more.
"""

import os
import pandas as pd
import fastf1
from fastf1.exceptions import RateLimitExceededError
from tqdm import tqdm

from backend.config import BASE_DIR, SEASONS, CACHE_DIR
from backend.src.data.data_pipeline import load_race_session, extract_race_data, extract_practice_pace

fastf1.Cache.enable_cache(CACHE_DIR)
SEASONS_DIR = os.path.join(BASE_DIR, "data", "processed", "seasons")
CURRENT_YEAR = pd.Timestamp.utcnow().year


def completed_rounds(year: int) -> list:
    """Race rounds for `year` whose race session is already in the past."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    schedule = schedule[schedule["EventFormat"] != "testing"]
    rounds = schedule["RoundNumber"].tolist()
    if "Session5DateUtc" in schedule.columns:
        now = pd.Timestamp.utcnow().tz_localize(None)
        race_dt = pd.to_datetime(schedule["Session5DateUtc"]).dt.tz_localize(None)
        done = schedule[race_dt < now]["RoundNumber"].tolist()
        rounds = [r for r in rounds if r in done]
    return rounds


def _saved_rounds(season_path: str) -> set:
    if not os.path.exists(season_path):
        return set()
    try:
        return set(pd.read_csv(season_path, usecols=["RoundNumber"])["RoundNumber"].astype(int))
    except Exception:
        return set()


def next_season_to_pull():
    """First season needing work: a missing file, or the in-progress season
    that's behind on completed rounds."""
    os.makedirs(SEASONS_DIR, exist_ok=True)
    for year in SEASONS:
        season_path = os.path.join(SEASONS_DIR, f"season_{year}.csv")
        if not os.path.exists(season_path):
            return year
        if year >= CURRENT_YEAR:                       # in-progress season: check freshness
            try:
                expected = set(completed_rounds(year))
            except Exception:
                expected = set()
            missing = expected - _saved_rounds(season_path)
            if missing:
                print(f"{year} behind by rounds {sorted(missing)} -> refreshing")
                return year
    return None


def pull_one_season(year: int) -> bool:
    """Pull all completed rounds for a season. Returns True if saved."""
    rounds = completed_rounds(year)
    print(f"\nSeason {year}: {len(rounds)} completed rounds to pull")
    season_races = []
    for rnd in tqdm(rounds, desc=str(year)):
        try:
            race, quali = load_race_session(year, rnd)
            race_data = extract_race_data(race, quali)
            practice = extract_practice_pace(year, rnd)
            if not practice.empty:
                race_data = race_data.merge(practice, on="Driver", how="left")
            season_races.append(race_data)
        except RateLimitExceededError:
            print(f"\n  Rate limit hit at {year} R{rnd}. "
                  f"Stopping WITHOUT saving — re-run to resume (cached rounds are free).")
            return False
        except Exception as e:
            print(f"  Skipping {year} R{rnd}: {e}")
            continue

    if not season_races:
        print(f"  No data pulled for {year}; not writing a file.")
        return False

    season_df = pd.concat(season_races, ignore_index=True)
    season_path = os.path.join(SEASONS_DIR, f"season_{year}.csv")
    season_df.to_csv(season_path, index=False)   # overwrites — refreshes in-progress season
    print(f"Saved {year}: {season_df['RoundNumber'].nunique()} rounds, {len(season_df)} rows")
    return True


if __name__ == "__main__":
    year = next_season_to_pull()
    if year is None:
        print("All seasons in SEASONS are pulled and up to date.")
    else:
        print(f"Next season to pull: {year}")
        pull_one_season(year)
