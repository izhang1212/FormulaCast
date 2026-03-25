# Transform raw race data into ML - ready features

import pandas as pd
import numpy as np

def add_driver_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    # add rolling performance stats per driver

    df = df.sort_values(["Driver", "Year", "RoundNumber"]).copy()
    grouped = df.groupby("Driver")

    # Rolling average finsih position (last 3 and 5 races)

    df["AvgPoints_Last5"] = grouped["Points"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )

    # Rolling DNF rate
    df["DNFRate_Last10"] = grouped["DNF"].transform(
        lambda x: x.shift(1).astype(float).rolling(10, min_periods=1).mean()
    )

    # Career race count at this point
    df["CareerRaces"] = grouped.cumcount()

    return df

# Add rolling constructor-level stats
def add_constructor_features(df: pd.DataFrame) -> pd.DataFrame:

    df = df.sort_values(["Team", "Year", "RoundNumber"]).copy()

    grouped = df.groupby("Team")

    # Team average finish (both drivers combined)
    df["TeamAvgFinish_Last5"] = grouped["FinishPosition"].transform(
        lambda x: x.shift(1).rolling(10, min_periods=2).mean()
    )

    # Team DNF rate
    df["TeamDNFRate_Last10"] = grouped["DNF"].transform(
        lambda x: x.shift(1).astype(float).rolling(20, min_periods=2).mean()
    )

    # Team average pit stops per race
    df["TeamAvgPitStops"] = grouped["NumPitStops"].transform(
        lambda x: x.shift(1).rolling(10, min_periods=2).mean()
    )

    return df

# Add features derived from grid positions
def add_qualifying_features(df: pd.DataFrame) -> pd.DataFrame:

    # Grid position relative to field (0 = pole, 1 = last)
    race_groups = df.groupby(["Year", "RoundNumber"])
    df["GridPositionNorm"] = race_groups["GridPosition"].transform(
        lambda x: (x - x.min()) / (x.max() - x.min() + 1e-6)
    )

    # Historical grid-to-finish conversion (does this driver usually gain or lose positions?)
    df["GridToFinishDelta"] = df["FinishPosition"] - df["GridPosition"]
    df["AvgGridDelta_Last5"] = (
        df.sort_values(["Driver", "Year", "RoundNumber"])
        .groupby("Driver")["GridToFinishDelta"]
        .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
    )

    return df

# Add circuit specific historical features
def add_track_features(df: pd.DataFrame) -> pd.DataFrame:

    df = df.sort_values(["Driver", "Year", "RoundNumber"]).copy()

    # Driver's average finish at this specific circuit (historical)
    df["DriverTrackAvgFinish"] = (
        df.groupby(["Driver", "CircuitName"])["FinishPosition"]
        .transform(lambda x: x.shift(1).expanding().mean())
    )

    # Number of times driver has raced at this track before
    df["DriverTrackExperience"] = (
        df.groupby(["Driver", "CircuitName"]).cumcount()
    )

    return df

# Bin weather into simple categories
    # E.g. rain, wind, temp
def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    df["IsWetRace"] = df["Rainfall"].astype(int)
    df["IsHotRace"] = (df["AvgTrackTemp"] > df["AvgTrackTemp"].quantile(0.75)).astype(int)
    df["IsWindy"] = (df["AvgWindSpeed"] > df["AvgWindSpeed"].quantile(0.75)).astype(int)

    return df
    
# Add exponentially weighted stats that bias toward recent races.
    # More recent races impact decision/prediction more
def add_weighted_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Driver", "Year", "RoundNumber"]).copy()

    grouped = df.groupby("Driver")

    # Driver: halflife=6 (a race 6 rounds ago still counts 50%)
    df["EWM_Finish"] = grouped["FinishPosition"].transform(
        lambda x: x.shift(1).ewm(halflife=6, min_periods=1).mean()
    )

    # Exponentially weighted points
    df["EWM_Points"] = grouped["Points"].transform(
        lambda x: x.shift(1).ewm(halflife=6, min_periods=1).mean()
    )

    # Constructor halflife = 8
    df["Team_EWM_Finish"] = (
        df.sort_values(["Team", "Year", "RoundNumber"])
        .groupby("Team")["FinishPosition"]
        .transform(lambda x: x.shift(1).ewm(halflife=8, min_periods=2).mean())
    )

    return df

# Apply all feature engineering steps
    # Returns: DataFrame with all new columns added
def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:

    print("Adding driver rolling features...")
    df = add_driver_rolling_features(df)

    print("Adding weighted features...")
    df = add_weighted_features(df)

    print("Adding constructor features...")
    df = add_constructor_features(df)

    print("Adding qualifying features...")
    df = add_qualifying_features(df)

    print("Adding track features...")
    df = add_track_features(df)

    print("Adding weather features...")
    df = add_weather_features(df)

    # Drop rows where we don't have enough history yet
    df = df.dropna(subset=["AvgFinish_Last3"])

    print(f"Feature matrix: {len(df)} rows, {len(df.columns)} columns")
    return df


# The columns the RF model will actually train on
FEATURE_COLUMNS = [
    "GridPosition",
    "GridPositionNorm",
    "AvgFinish_Last3",
    "AvgFinish_Last5",
    "AvgPoints_Last5",
    "EWM_Finish",
    "EWM_Points",
    "DNFRate_Last10",
    "CareerRaces",
    "TeamAvgFinish_Last5",
    "TeamDNFRate_Last10",
    "TeamAvgPitStops",
    "Team_EWM_Finish",
    "AvgGridDelta_Last5",
    "DriverTrackAvgFinish",
    "DriverTrackExperience",
    "AvgAirTemp",
    "AvgTrackTemp",
    "AvgWindSpeed",
    "IsWetRace",
    "IsHotRace",
    "IsWindy",
]

TARGET_COLUMN = "FinishPosition"