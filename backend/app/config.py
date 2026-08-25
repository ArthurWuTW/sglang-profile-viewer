from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _default_mappings_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "mappings"


def _default_frontend_dist() -> Path:
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


@dataclass(frozen=True)
class Settings:
    profile_root: Path
    host: str
    port: int
    watch_interval: float
    file_stability_delay: float
    max_loaded_profiles: int
    max_events_per_response: int
    log_level: str
    mappings_dir: Path
    frontend_dist: Path | None

    @classmethod
    def from_env(cls, overrides: dict | None = None) -> "Settings":
        o = overrides or {}
        profile_root = Path(o.get("profile_root") or _env("PROFILE_ROOT", "/root/.cache/profile_log"))
        mappings_dir = Path(o.get("mappings_dir") or _env("MAPPINGS_DIR", str(_default_mappings_dir())))
        frontend_dist_raw = o.get("frontend_dist", _env("FRONTEND_DIST", str(_default_frontend_dist())))
        frontend_dist = Path(frontend_dist_raw) if frontend_dist_raw else None
        return cls(
            profile_root=profile_root,
            host=o.get("host") or _env("HOST", "0.0.0.0"),
            port=_env_int("PORT", 6006),
            watch_interval=_env_float("WATCH_INTERVAL", 2.0),
            file_stability_delay=_env_float("FILE_STABILITY_CHECK_DELAY", 1.0),
            max_loaded_profiles=_env_int("MAX_LOADED_PROFILES", 3),
            max_events_per_response=_env_int("MAX_EVENTS_PER_RESPONSE", 10000),
            log_level=o.get("log_level") or _env("LOG_LEVEL", "INFO"),
            mappings_dir=mappings_dir,
            frontend_dist=frontend_dist,
        )
