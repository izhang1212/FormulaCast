import os
from src.data_pipeline import build_master_dataset

DATA_OUTPUT_PATH = os.path.join("data", "processed", "master_race_data.csv")


def run_pipeline():
    """Phase 1: Build the master dataset."""
    os.makedirs(os.path.dirname(DATA_OUTPUT_PATH), exist_ok=True)
    df = build_master_dataset()
    df.to_csv(DATA_OUTPUT_PATH, index=False)
    print(f"Saved to {DATA_OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    df = run_pipeline()