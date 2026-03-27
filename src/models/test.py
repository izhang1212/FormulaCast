# Test accuracy of simulation and real life

import pandas as pd
from src.models.monte_carlo import run_simulation


def backtest_race(race_data: pd.DataFrame, total_laps: int, n_sims: int = 5000) -> pd.DataFrame:
    results = run_simulation(race_data, total_laps, n_sims)
    summary = results["summary"]

    comparison = summary[["Driver", "ExpectedPosition", "WinProb", "PodiumProb"]].copy()
    actuals = race_data[["Driver", "FinishPosition"]].copy()

    comparison = comparison.merge(actuals, on="Driver")
    comparison["Error"] = abs(comparison["ExpectedPosition"] - comparison["FinishPosition"])
    comparison = comparison.sort_values("FinishPosition")

    return comparison