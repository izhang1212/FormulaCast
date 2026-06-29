import io
import os
from pathlib import Path

from backend.config import DATA_ROOT


SEASON_PREFIX = "processed/seasons"
LIVE_STATE_REMOTE = "processed/live_state.joblib"


def supabase_is_configured() -> bool:
    return bool(
        os.environ.get("SUPABASE_URL")
        and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        and os.environ.get("SUPABASE_BUCKET")
    )


def hydrate_seasons_from_supabase(target_dir: str | Path | None = None) -> list[str]:
    """Download season CSVs from Supabase Storage into the runtime data folder."""
    if not supabase_is_configured():
        return []

    from supabase import create_client

    target = Path(target_dir or Path(DATA_ROOT) / "processed" / "seasons")
    target.mkdir(parents=True, exist_ok=True)

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    bucket = os.environ["SUPABASE_BUCKET"]
    storage = supabase.storage.from_(bucket)
    files = storage.list(SEASON_PREFIX)

    downloaded = []
    for item in files:
        name = item.get("name") if isinstance(item, dict) else getattr(item, "name", "")
        if not name or not name.endswith(".csv"):
            continue
        remote_path = f"{SEASON_PREFIX}/{name}"
        content = storage.download(remote_path)
        local_path = target / name
        local_path.write_bytes(content)
        downloaded.append(name)

    return downloaded


def push_seasons_to_supabase(source_dir: str | Path | None = None) -> list[str]:
    """Upload local season CSVs from source_dir to Supabase Storage.

    Existing remote files are replaced (remove then re-upload) so the bucket
    always mirrors the local state after this call.
    """
    if not supabase_is_configured():
        return []

    from supabase import create_client

    source = Path(source_dir or Path(DATA_ROOT) / "processed" / "seasons")
    if not source.exists():
        return []

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    bucket = os.environ["SUPABASE_BUCKET"]
    storage = supabase.storage.from_(bucket)

    uploaded = []
    for csv_file in sorted(source.glob("season_*.csv")):
        remote_path = f"{SEASON_PREFIX}/{csv_file.name}"
        content = csv_file.read_bytes()

        # Remove first so upload never hits a "file already exists" conflict.
        try:
            storage.remove([remote_path])
        except Exception:
            pass

        storage.upload(remote_path, content)
        uploaded.append(csv_file.name)
        print(f"  ↑ {csv_file.name}")

    return uploaded


def push_live_state(state: dict) -> bool:
    """Serialize and upload the live prediction state (RF model + feature rows) to Supabase."""
    if not supabase_is_configured():
        print("Supabase not configured — live state not uploaded.")
        return False

    import joblib
    from supabase import create_client

    buf = io.BytesIO()
    joblib.dump(state, buf, compress=3)
    content = buf.getvalue()

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    storage = supabase.storage.from_(os.environ["SUPABASE_BUCKET"])

    try:
        storage.remove([LIVE_STATE_REMOTE])
    except Exception:
        pass

    storage.upload(LIVE_STATE_REMOTE, content)
    print(f"  ↑ live_state.joblib ({len(content) / 1024 / 1024:.1f} MB)")
    return True


def pull_live_state() -> "dict | None":
    """Download and deserialize the live prediction state from Supabase."""
    if not supabase_is_configured():
        return None

    import joblib
    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    storage = supabase.storage.from_(os.environ["SUPABASE_BUCKET"])

    try:
        content = storage.download(LIVE_STATE_REMOTE)
        state = joblib.load(io.BytesIO(content))
        print(f"  ↓ live_state.joblib ({len(content) / 1024 / 1024:.1f} MB)")
        return state
    except Exception as exc:
        print(f"Could not pull live state from Supabase: {exc}")
        return None
