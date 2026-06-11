import os
from pathlib import Path

from backend.config import DATA_ROOT


SEASON_PREFIX = "processed/seasons"


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
