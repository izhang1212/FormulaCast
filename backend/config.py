from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent   # the backend/ folder
PROJECT_ROOT = BASE_DIR.parent
_VERCEL_RUNTIME = bool(os.environ.get("VERCEL"))
_RUNTIME_ROOT = Path(os.environ.get(
    "FORMULACAST_RUNTIME_ROOT",
    "/tmp/formulacast" if _VERCEL_RUNTIME else BASE_DIR,
))
DATA_ROOT = Path(os.environ.get(
    "FORMULACAST_DATA_ROOT",
    _RUNTIME_ROOT / "data" if _VERCEL_RUNTIME else BASE_DIR / "data",
))
CACHE_DIR = os.environ.get(
    "FORMULACAST_CACHE_DIR",
    str(_RUNTIME_ROOT / "f1_cache" if _VERCEL_RUNTIME else BASE_DIR / "f1_cache"),
)
os.makedirs(CACHE_DIR, exist_ok=True)

PREDICTIONS_DIR = DATA_ROOT / "predictions"

SEASONS = list(range(2018, 2027))

# Random Forest Parameters
RF_PARAMS = {
    "n_estimators": 2000,
    "max_depth": 5,
    "min_samples_split": 20,
    "min_samples_leaf": 10,
    "max_features": 0.5,
    "random_state": 42,
    "n_jobs": -1,
}

# Monte Carlo
NUM_SIMULATIONS = 20_000
MC_RANDOM_SEED = 42

POINTS_SYSTEM = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1,
}
