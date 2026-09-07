"""Structured logging with job and stage context.

Named `logs` rather than `logging` to avoid the shadowing footgun.
Python 3's absolute imports would technically make `sagar_core/logging.py`
safe, but anyone reading `import logging` inside this package would have
to stop and work that out, and a filename is a cheap thing to get out of
the way.

Output is JSON lines. The pipeline's long stages emit progress that the
API surfaces to the operator console as NAMED STAGES, never percentages
(docs/api/API_CONTRACT.md): "advecting 50 vessels x 96 release times"
tells an analyst what is happening, "63%" does not.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

#: Ambient job/stage context, carried without threading it through every
#: function signature. A ContextVar rather than a global so concurrent
#: jobs in the same worker process cannot bleed into each other's logs.
#:
#: Defaults to None rather than {}: a mutable default is a single shared
#: instance, so any future code doing `_context.get()["k"] = v` instead
#: of a rebinding `.set()` would silently corrupt every context. Read it
#: through `_current()`, never directly.
_context: ContextVar[dict[str, Any] | None] = ContextVar("sagar_log_context", default=None)


def _current() -> dict[str, Any]:
    return _context.get() or {}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_current())
        # Anything passed via `extra=` wins over ambient context.
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__ and key != "extra":
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure(level: str = "INFO") -> None:
    """Install the JSON handler on the root logger. Idempotent."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for existing in list(root.handlers):
        if getattr(existing, "_sagar", False):
            return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler._sagar = True  # type: ignore[attr-defined]
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@contextmanager
def job_context(**fields: Any) -> Iterator[None]:
    """Attach fields to every log line emitted inside the block.

        with job_context(job_id="job_01H", stage="advecting"):
            log.info("seeded particles", extra={"vessels": 50})

    Restores the previous context on exit, including when the block
    raises — a stage that fails must not leak its stage name into
    whatever runs next.
    """
    token = _context.set({**_current(), **fields})
    try:
        yield
    finally:
        _context.reset(token)


#: The named stages the API contract exposes. Kept here so a worker
#: cannot invent a stage name the console has never heard of.
STAGES = (
    "preprocessing",
    "detecting",
    "filtering",
    "hindcasting",
    "gating_traffic",
    "advecting",
    "scoring",
    "forecasting",
    "building_dossier",
)


def validate_stage(stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {', '.join(STAGES)}")
    return stage
