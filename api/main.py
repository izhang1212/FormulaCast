from __future__ import annotations

import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import BASE_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_DIR = (BASE_DIR / "data" / "predictions").resolve()
FRONTEND_PREDICTIONS_DIR = (PROJECT_ROOT / "frontend" / "public" / "predictions").resolve()


class RefreshRequest(BaseModel):
    update_seasons: bool = True
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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


@app.post("/api/refresh/local", response_model=RefreshState, status_code=202)
def refresh_local(background_tasks: BackgroundTasks):
    return _schedule_refresh(
        background_tasks,
        RefreshRequest(
            update_seasons=False,
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
