"""
prepare_future.py — Turn stored future race rows into a model-ready feature matrix

future_races.csv can't be fed to the model directly: nearly every feature is a
rolling/EWM lookback over a driver's PRIOR races. With no history in the frame they
come out empty. So: load history, concat the future rows, build features on the
combined set (shift(1) pulls each driver's real history into their upcoming row),
then slice the future rows back out. GridPosition is left NaN by design — the grid
model or official grid fills it later.
"""

import os
import glob
import pandas as pd

# Adjust to match your layout if feature_engineering isn't a sibling import.
from src.data.feature_engineering import build_feature_matrix, FEATURE_COLUMNS

SEASONS_DIR = os.path.join("data", "processed", "seasons")
FUTURE_PATH = os.path.join("data", "processed", "future_races.csv")
_LEAVE_NAN = {"GridPosition"}   # filled later by sampled/official grid


def load_history() -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(SEASONS_DIR, "season_*.csv")))
    if not files:
        raise FileNotFoundError(f"No season files in {SEASONS_DIR}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def prepare_future_for_prediction(future_path=FUTURE_PATH) -> pd.DataFrame:
    if not os.path.exists(future_path):
        raise FileNotFoundError(
            f"{future_path} not found — run future_races.py first to generate it."
        )

    hist = load_history()
    future = pd.read_csv(future_path)
    hist["_is_future"], future["_is_future"] = False, True

    combined = pd.concat([hist, future], ignore_index=True, sort=False)
    feat = build_feature_matrix(combined)
    fut = feat[feat["_is_future"]].copy()

    # Impute residual NaN in model features from historical medians, so new teams
    # or sparse-history drivers don't carry NaN into the RF. GridPosition excluded.
    hist_feat = feat[~feat["_is_future"]]
    impute_cols = [c for c in FEATURE_COLUMNS if c not in _LEAVE_NAN]
    fut[impute_cols] = fut[impute_cols].fillna(hist_feat[impute_cols].median(numeric_only=True))

    pending = fut["GridPosition"].isna().sum()
    print(f"Prepared {len(fut)} future rows across {fut['CircuitName'].nunique()} races "
          f"({pending} awaiting GridPosition).")
    return fut
