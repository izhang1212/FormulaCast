# Transform raw race data into ML - ready features

import pandas as pd
import numpy as np

def add_driver_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    # add rolling performance stats per driver

    df = df.sort_values(["Driver", "Year", "RoundNumber"]).copy()
    grouped = df.groupby("Driver")

    # Rolling average finsih position (last 3 and 5 races)

    df["AvgFinish_Last3"] = grouped["FinishPosition"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    )
    df["AvgFinish_Last5"] = grouped["FinishPosition"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )

    df["AvgPoints_Last5"] = grouped["Points"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )

    # Rolling DNF rate
    df["DNFRate_Last10"] = grouped["DNF"].transform(
        lambda x: x.shift(1).astype(float).rolling(10, min_periods=1).mean()
    )

    # Career race count at this point
    df["CareerRaces"] = grouped.cumcount()

    df["PointsMomentum_Last3"] = grouped["Points"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).sum()
    )

    # Best finish in last 5
    df["BestFinish_Last5"] = grouped["FinishPosition"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).min()
    )

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

    race_avg = df.groupby(["Year", "RoundNumber"])["EWM_Finish"].transform("mean")
    df["FieldStrength"] = race_avg

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
        lambda x: x.shift(1).ewm(halflife=4, min_periods=1).mean()
    )
    df["EWM_Points"] = grouped["Points"].transform(
        lambda x: x.shift(1).ewm(halflife=4, min_periods=1).mean()
    )

    # Constructor halflife = 5
    df["Team_EWM_Finish"] = (
        df.sort_values(["Team", "Year", "RoundNumber"])
        .groupby("Team")["FinishPosition"]
        .transform(lambda x: x.shift(1).ewm(halflife=5, min_periods=2).mean())
    )

    return df

def add_race_pace_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features that capture actual race pace vs qualifying pace."""
    df = df.sort_values(["Driver", "Year", "RoundNumber"]).copy()

    # How much faster/slower is this driver vs their teammate in races?
    team_avg = df.groupby(["Year", "RoundNumber", "Team"])["FinishPosition"].transform("mean")
    df["VsTeammateDelta"] = df["FinishPosition"] - team_avg

    df["AvgVsTeammate_Last5"] = (
        df.groupby("Driver")["VsTeammateDelta"]
        .transform(lambda x: x.shift(1).ewm(halflife=5, min_periods=1).mean())
    )

    # Consistency: std dev of recent finishes (low = consistent, high = volatile)
    df["FinishStd_Last5"] = (
        df.groupby("Driver")["FinishPosition"]
        .transform(lambda x: x.shift(1).rolling(5, min_periods=2).std())
    )

    # Grid-to-finish conversion rate (does this driver GAIN or LOSE positions?)
    df["PositionChange"] = df["GridPosition"] - df["FinishPosition"]  # Positive = gained positions
    df["EWM_PositionChange"] = (
        df.groupby("Driver")["PositionChange"]
        .transform(lambda x: x.shift(1).ewm(halflife=5, min_periods=1).mean())
    )

    # Did the driver DNF last race? (momentum/reliability signal)
    df["DNF_LastRace"] = (
        df.groupby("Driver")["DNF"]
        .transform(lambda x: x.shift(1).fillna(0))
    ).astype(int)

    return df


def add_grid_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features that interact grid position with other signals."""
    # Gap between grid and recent form (overqualified or underqualified?)
    df["GridVsForm"] = df["GridPosition"] - df["EWM_Finish"]
    # Positive = qualified better than recent form suggests (overperformance risk)
    # Negative = qualified worse than form (likely to gain positions)

    # Field strength: how strong is the rest of the grid this race?
    race_avg = df.groupby(["Year", "RoundNumber"])["EWM_Finish"].transform("mean")
    df["FieldStrength"] = race_avg

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

    print("Adding race pace features...")
    df = add_race_pace_features(df)

    print("Adding grid interaction features...")
    df = add_grid_interaction_features(df)

    cols_to_check = [c for c in ["AvgFinish_Last3"] if c in df.columns]
    if cols_to_check:
        df = df.dropna(subset=cols_to_check)

    print(f"Feature matrix: {len(df)} rows, {len(df.columns)} columns")
    return df


# The columns the RF model will actually train on
FEATURE_COLUMNS = [
    "GridPosition",
    "EWM_Finish",
    "EWM_Points",
    "Team_EWM_Finish",
    "AvgGridDelta_Last5",
    "EWM_PositionChange",
    "AvgVsTeammate_Last5",
    "FinishStd_Last5",
    "DNFRate_Last10",
    "DriverTrackAvgFinish",
    "PointsMomentum_Last3",
    "BestFinish_Last5",
    "TeamAvgFinish_Last5",
    "CareerRaces",
    "DNF_LastRace",
    "FieldStrength",
]

TARGET_COLUMN = "FinishPosition"