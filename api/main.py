from __future__ import annotations

import json
import os
import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import DATA_ROOT


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_DIR = (DATA_ROOT / "predictions").resolve()
FRONTEND_PREDICTIONS_DIR = (PROJECT_ROOT / "frontend" / "public" / "predictions").resolve()


class RefreshRequest(BaseModel):
    update_seasons: bool = True
    hydrate_supabase: bool = False
    rebuild_local_data: bool = False
    historical: bool = True
    future: bool = True
    performance: bool = True
    sync_frontend: bool = True
    force_future_schedule: bool = True
    max_seasons: int = Field(default=1, ge=0, le=10)


class RefreshState(BaseModel):
    state: Literal["idle", "running", "succeeded", "failed"] = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    message: str = "No refresh has run yet."
    details: list[str] = Field(default_factory=list)


app = FastAPI(
    title="FormulaCast API",
    version="1.0.0",
    description="Serves FormulaCast prediction JSON and refreshes model exports.",
)

_frontend_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        *_frontend_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_refresh_lock = threading.Lock()
_refresh_state = RefreshState()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_refresh_state(**updates) -> None:
    global _refresh_state
    current = _refresh_state.dict()
    current.update(updates)
    _refresh_state = RefreshState(**current)


def _prediction_path(relative_path: str) -> Path:
    requested = (PREDICTIONS_DIR / relative_path).resolve()
    try:
        requested.relative_to(PREDICTIONS_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid prediction path") from exc
    if requested.suffix != ".json":
        raise HTTPException(status_code=400, detail="Prediction path must be a JSON file")
    return requested


def _copy_predictions_to_frontend() -> None:
    if not PREDICTIONS_DIR.exists():
        raise FileNotFoundError(f"Predictions directory not found: {PREDICTIONS_DIR}")
    FRONTEND_PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PREDICTIONS_DIR, FRONTEND_PREDICTIONS_DIR, dirs_exist_ok=True)


def _update_completed_seasons(max_seasons: int) -> list[int]:
    from backend.update_seasons import next_season_to_pull, pull_one_season

    updated: list[int] = []
    for _ in range(max_seasons):
        year = next_season_to_pull()
        if year is None:
            break
        if pull_one_season(year):
            updated.append(int(year))
        else:
            break
    return updated


def _hydrate_supabase_seasons() -> list[str]:
    from backend.cloud_storage import hydrate_seasons_from_supabase

    return hydrate_seasons_from_supabase()


def _force_future_rebuild() -> None:
    from backend.main import FUTURE_PATH

    future_path = Path(FUTURE_PATH)
    if future_path.exists():
        future_path.unlink()


def _force_local_data_rebuild() -> list[str]:
    from backend.main import DATA_OUTPUT_PATH, FEATURES_OUTPUT_PATH

    cleared = []
    for path_value in [FEATURES_OUTPUT_PATH, DATA_OUTPUT_PATH]:
        path = Path(path_value)
        if path.exists():
            path.unlink()
            cleared.append(path.name)
    return cleared


def _run_refresh_job(request: RefreshRequest, lock_acquired: bool = False) -> None:
    if not lock_acquired and not _refresh_lock.acquire(blocking=False):
        return

    details: list[str] = []
    try:
        _set_refresh_state(
            state="running",
            started_at=_now_iso(),
            finished_at=None,
            message="Refresh is running.",
            details=[],
        )

        if request.update_seasons and request.max_seasons > 0:
            updated = _update_completed_seasons(request.max_seasons)
            details.append(
                f"Updated season files: {', '.join(map(str, updated)) if updated else 'none needed'}."
            )

        if request.hydrate_supabase:
            downloaded = _hydrate_supabase_seasons()
            details.append(
                f"Downloaded Supabase season files: {', '.join(downloaded) if downloaded else 'none'}."
            )

        if request.rebuild_local_data:
            cleared = _force_local_data_rebuild()
            details.append(
                f"Cleared local build caches: {', '.join(cleared) if cleared else 'none present'}."
            )

        if request.historical:
            from backend.exporters import export_historical_predictions

            export_historical_predictions()
            details.append("Exported historical prediction JSON.")

        if request.future:
            if request.force_future_schedule:
                _force_future_rebuild()
                details.append("Forced upcoming race schedule rebuild.")

            from backend.exporters import export_future_predictions

            export_future_predictions()
            details.append("Exported future prediction JSON.")

        if request.performance:
            from backend.exporters import export_performance

            export_performance()
            details.append("Exported performance JSON.")

        if request.sync_frontend:
            _copy_predictions_to_frontend()
            details.append("Synced predictions into frontend/public/predictions.")

        _set_refresh_state(
            state="succeeded",
            finished_at=_now_iso(),
            message="Refresh completed.",
            details=details,
        )
    except Exception as exc:
        details.append(traceback.format_exc())
        _set_refresh_state(
            state="failed",
            finished_at=_now_iso(),
            message=f"Refresh failed: {exc}",
            details=details,
        )
    finally:
        _refresh_lock.release()


def _schedule_refresh(background_tasks: BackgroundTasks, request: RefreshRequest) -> RefreshState:
    if os.environ.get("VERCEL"):
        if not _refresh_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="A refresh is already running")
        _run_refresh_job(request, True)
        return _refresh_state

    if not _refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A refresh is already running")

    _set_refresh_state(
        state="running",
        started_at=_now_iso(),
        finished_at=None,
        message="Refresh queued.",
        details=[],
    )
    background_tasks.add_task(_run_refresh_job, request, True)
    return _refresh_state


def _read_json(path: Path):
    with open(path) as f:
        return json.load(f)


def _collect_prediction_payloads() -> dict:
    payload = {
        "racesIndex": [],
        "races": {},
        "futureIndex": [],
        "future": {},
        "performance": None,
    }

    races_path = PREDICTIONS_DIR / "races.json"
    if races_path.exists():
        payload["racesIndex"] = _read_json(races_path)
        for race in payload["racesIndex"]:
            key = f"{race['year']}/round_{race['round']}"
            path = PREDICTIONS_DIR / str(race["year"]) / f"round_{race['round']}.json"
            if path.exists():
                payload["races"][key] = _read_json(path)

    future_index_path = PREDICTIONS_DIR / "future" / "index.json"
    if future_index_path.exists():
        payload["futureIndex"] = _read_json(future_index_path)
        for race in payload["futureIndex"]:
            key = f"{race['year']}_round_{race['round']}"
            path = PREDICTIONS_DIR / "future" / f"{key}.json"
            if path.exists():
                payload["future"][key] = _read_json(path)

    performance_path = PREDICTIONS_DIR / "performance.json"
    if performance_path.exists():
        payload["performance"] = _read_json(performance_path)

    return payload


# ---------------------------------------------------------------------------
# Live prediction endpoint — runs a fresh Monte Carlo per user visit.
#
# Cold start path (first request):
#   1. Try to download a pre-built state from Supabase (RF model + feature rows,
#      uploaded by the weekly GitHub Actions workflow).  Fast: ~1-2 s download.
#   2. If Supabase isn't configured or the blob is missing, fall back to running
#      the full local pipeline (useful for local dev with season CSVs on disk).
#
# Warm path (subsequent requests on the same serverless instance):
#   The state dict is cached in _live_cache so only the MC (seed=None →
#   unique per visitor, ~3-8 s) needs to run.
# ---------------------------------------------------------------------------

_live_cache: dict | None = None


def _to_python(val):
    """Convert numpy/pandas scalars to JSON-safe Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _build_live_state_from_local() -> dict:
    """Fallback: build the live state from season CSVs on disk (local dev path)."""
    from backend.exporters import train_model_on_all_history
    from backend.main import DATA_OUTPUT_PATH, ensure_future_file, run_features, run_pipeline
    from backend.src.future.predict_future import (
        get_race_rows,
        list_future_races,
        load_future_races,
    )
    from backend.src.models.track_calibration import calibrate_track_events

    df = run_pipeline()
    features = run_features(df)
    model = train_model_on_all_history(features)
    raw_df = pd.read_csv(DATA_OUTPUT_PATH)
    track_calibration = calibrate_track_events(raw_df)

    future_path = ensure_future_file()
    future = load_future_races(future_path)
    races = list_future_races(future).reset_index(drop=True)

    race_rows: dict = {}
    race_index: list = []
    for _, race in races.iterrows():
        year = int(race["Year"])
        round_no = int(race["RoundNumber"])
        name = str(race["CircuitName"])
        rows = get_race_rows(future, year, round_no)
        key = f"{year}_round_{round_no}"
        race_rows[key] = rows
        race_index.append({
            "year": year,
            "round": round_no,
            "name": name,
            "race_date": _to_python(rows["RaceDateUtc"].iloc[0]) if "RaceDateUtc" in rows.columns else None,
            "qualifying_date": _to_python(rows["QualifyingDateUtc"].iloc[0]) if "QualifyingDateUtc" in rows.columns else None,
        })

    return {
        "model": model,
        "track_calibration": track_calibration,
        "race_rows": race_rows,
        "race_index": race_index,
    }


@app.get("/api/predict/live")
def predict_live():
    """Return fresh Monte Carlo predictions for every upcoming race.

    Cold start: downloads pre-built state from Supabase (or falls back to local
    pipeline). Warm: uses cached model + race rows, runs fresh MC only (~3-8 s).
    Every visitor gets a unique simulation because seed=None.
    """
    global _live_cache

    if _live_cache is None:
        from backend.cloud_storage import pull_live_state

        state = pull_live_state()
        if state is None:
            state = _build_live_state_from_local()
        _live_cache = state

    from backend.src.future.predict_future import predict_future_race
    from backend.src.models.monte_carlo import COLUMN_MAP

    model = _live_cache["model"]
    track_cal = _live_cache["track_calibration"]

    future_index: list[dict] = []
    future_dict: dict = {}

    for entry in _live_cache["race_index"]:
        year = entry["year"]
        round_no = entry["round"]
        name = entry["name"]
        key = f"{year}_round_{round_no}"
        rows = _live_cache["race_rows"][key]

        results = predict_future_race(model, rows, track_cal, seed=None)
        summary = results["summary"].rename(columns=COLUMN_MAP)

        race_date = _to_python(entry.get("race_date"))
        quali_date = _to_python(entry.get("qualifying_date"))

        payload = {
            "year": year,
            "round": round_no,
            "name": name,
            "laps": int(results.get("total_laps", 57)),
            "mode": str(results.get("mode", "sampled")),
            "race_date": race_date,
            "qualifying_date": quali_date,
            "drivers": [
                {k: _to_python(v) for k, v in row.items()}
                for row in summary.to_dict(orient="records")
            ],
        }

        future_dict[key] = payload
        future_index.append({
            "year": year,
            "round": round_no,
            "name": name,
            "mode": payload["mode"],
            "race_date": race_date,
            "qualifying_date": quali_date,
        })

    return {"futureIndex": future_index, "future": future_dict}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "predictions_dir": str(PREDICTIONS_DIR),
        "frontend_predictions_dir": str(FRONTEND_PREDICTIONS_DIR),
    }


@app.get("/api/predictions/{relative_path:path}")
def get_prediction(relative_path: str):
    path = _prediction_path(relative_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Prediction file not found")
    return FileResponse(path, media_type="application/json", headers={"Cache-Control": "no-cache"})


@app.get("/api/refresh/status", response_model=RefreshState)
def get_refresh_status():
    return _refresh_state


@app.post("/api/refresh", response_model=RefreshState, status_code=202)
def refresh_all(background_tasks: BackgroundTasks, request: RefreshRequest = Body(default_factory=RefreshRequest)):
    return _schedule_refresh(background_tasks, request)


@app.post("/api/bootstrap")
def bootstrap():
    request = RefreshRequest(
        update_seasons=False,
        hydrate_supabase=True,
        rebuild_local_data=True,
        historical=True,
        future=True,
        performance=True,
        sync_frontend=False,
        force_future_schedule=True,
        max_seasons=0,
    )
    if not _refresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A refresh is already running")
    _run_refresh_job(request, True)
    if _refresh_state.state == "failed":
        raise HTTPException(status_code=500, detail=_refresh_state.message)
    return {
        "refresh": _refresh_state,
        "predictions": _collect_prediction_payloads(),
    }


@app.post("/api/refresh/local", response_model=RefreshState, status_code=202)
def refresh_local(background_tasks: BackgroundTasks):
    return _schedule_refresh(
        background_tasks,
        RefreshRequest(
            update_seasons=False,
            hydrate_supabase=True,
            rebuild_local_data=True,
            historical=True,
            future=True,
            performance=True,
            sync_frontend=False,
            force_future_schedule=True,
            max_seasons=0,
        ),
    )


@app.post("/api/refresh/historical", response_model=RefreshState, status_code=202)
def refresh_historical(background_tasks: BackgroundTasks):
    return _schedule_refresh(
        background_tasks,
        RefreshRequest(historical=True, future=False, performance=True, sync_frontend=True),
    )


@app.post("/api/refresh/future", response_model=RefreshState, status_code=202)
def refresh_future(background_tasks: BackgroundTasks):
    return _schedule_refresh(
        background_tasks,
        RefreshRequest(update_seasons=False, historical=False, future=True, performance=False, sync_frontend=True),
    )
