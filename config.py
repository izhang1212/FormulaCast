from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = os.path.join(os.path.dirname(__file__), "f1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

SEASONS = list(range(2018, 2026))

# Random Forest Parameters
RF_PARAMS = {
    "n_estimators" : 500,
    "max_depth": 12,
    "min_samples_split": 10,
    "min_sample_leaf": 4,
    "max_features": "sqrt",
    "random_state": 42,
    "n_jobs": -1
}

# Monte Carlo
NUM_SIMULATIONS = 10_000
MC_RANDOM_SEED = 42

POINTS_SYSTEM = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1,
}