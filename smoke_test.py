import fastf1
import os

os.makedirs("f1_cache", exist_ok=True)
fastf1.Cache.enable_cache("f1_cache")

session = fastf1.get_session(2024, "Bahrain", "R")
session.load()
print(f"Laps: {len(session.laps)}, Drivers: {list(session.laps['Driver'].unique())}")