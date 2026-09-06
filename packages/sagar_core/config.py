"""Layered settings: defaults, then environment.

No file-format layer yet. Compose already injects everything through the
environment (.env -> container env), so a YAML/TOML tier would be a
second source of truth solving a problem nobody currently has. Add it if
and when a real need appears.

Credentials are read here but never logged, never hashed into a
provenance record, and never serialised into a dossier. `Settings` has a
`__repr__` that redacts them, because the most common way a token leaks
is a stack trace or a debug print, not a committed file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

#: Fixed repo-wide. Changing this invalidates every trained checkpoint —
#: it is a breaking change requiring a new ADR, not a tuning knob.
#: See docs/adr/0002-fixed-ground-sample-distance.md.
DEFAULT_GSD_METRES = 40.0

#: The wind speed band within which SAR oil detection is physically
#: meaningful. Outside it, detections are down-weighted with a logged
#: reason rather than silently trusted (PRD §2.2).
WIND_WINDOW_MS = (2.0, 12.0)

#: Terrestrial AIS receivers reach roughly this far offshore. Beyond it a
#: reporting gap is radio physics, not evasion, and the gap-anomaly
#: factor must be discounted accordingly (SCORING_MODEL §2.1(c)).
TERRESTRIAL_AIS_RANGE_NM = (40.0, 75.0)

#: Below this many recorded positions a vessel's gap baseline exists but
#: is not trusted. Mirrors MIN_SAMPLES_FOR_BASELINE in the API layer —
#: keep the two in step.
MIN_SAMPLES_FOR_BASELINE = 30


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_path(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default))


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be a number, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Resolved settings. Construct via `Settings.load()`."""

    data_root: Path = Path("/data")
    cache_root: Path = Path("/data/cache")
    demo_root: Path = Path("/data/demo")

    database_url: str = ""
    redis_url: str = ""

    #: Cache-only mode. A cache MISS RAISES rather than silently fetching
    #: over the network — the difference between failing loudly at setup
    #: and hanging mid-demo at a venue with no wifi (docs/OFFLINE_MODE.md).
    offline: bool = False

    gsd_metres: float = DEFAULT_GSD_METRES
    log_level: str = "INFO"

    #: Credentials. Redacted in repr; see the class docstring.
    cdse_client_id: str = field(default="", repr=False)
    cdse_client_secret: str = field(default="", repr=False)
    aisstream_api_key: str = field(default="", repr=False)

    _SECRET_FIELDS = ("cdse_client_id", "cdse_client_secret", "aisstream_api_key")

    @classmethod
    def load(cls) -> Settings:
        return cls(
            data_root=_env_path("DATA_ROOT", "/data"),
            cache_root=_env_path("CACHE_ROOT", "/data/cache"),
            demo_root=_env_path("DEMO_ROOT", "/data/demo"),
            database_url=_env_str("DATABASE_URL", ""),
            redis_url=_env_str("REDIS_URL", ""),
            offline=_env_bool("SAGAR_OFFLINE", False),
            gsd_metres=_env_float("SAGAR_GSD_METRES", DEFAULT_GSD_METRES),
            log_level=_env_str("SAGAR_LOG_LEVEL", "INFO"),
            cdse_client_id=_env_str("CDSE_CLIENT_ID", ""),
            cdse_client_secret=_env_str("CDSE_CLIENT_SECRET", ""),
            aisstream_api_key=_env_str("AISSTREAM_API_KEY", ""),
        )

    def snapshot(self) -> dict[str, object]:
        """Non-secret settings, for hashing into a provenance record.

        Secrets are excluded by construction rather than filtered on the
        way out: a snapshot that has to remember to drop a field will
        eventually forget.
        """
        return {
            f.name: str(getattr(self, f.name))
            for f in fields(self)
            if f.name not in self._SECRET_FIELDS
        }

    def __repr__(self) -> str:
        shown = ", ".join(
            f"{f.name}={getattr(self, f.name)!r}"
            for f in fields(self)
            if f.name not in self._SECRET_FIELDS
        )
        redacted = ", ".join(
            f"{name}={'<set>' if getattr(self, name) else '<unset>'}"
            for name in self._SECRET_FIELDS
        )
        return f"Settings({shown}, {redacted})"
