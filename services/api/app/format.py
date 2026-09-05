"""Centralised value formatting and validation for the API layer.

Mirrors web/src/lib/format.ts: consistent rendering of timestamps and
coordinates across the console, the API and the evidence dossier is what
separates a product from a prototype, and it only holds if there is
exactly one place that decides the format rather than a dozen call sites
each doing their own thing.

These are also enforcement points, not just formatters. docs/api/
API_CONTRACT.md is explicit that timestamps are "ISO 8601 UTC with an
explicit Z. Never a local format", and that geometry is "GeoJSON, WGS84,
longitude first". Both rules are easy to violate by accident (an offset
string instead of Z, a swapped lat/lon pair) and hard to notice in a code
review, so they are checked here and wired into the Pydantic schemas in
schemas.py rather than left as documentation alone.
"""

from __future__ import annotations

from datetime import UTC, datetime


def format_utc(dt: datetime) -> str:
    """Render a timestamp as ISO 8601 UTC with a literal trailing Z.

    Never `+00:00` — the contract calls for Z specifically, and a client
    doing a naive string comparison or display should not have to care
    about offset notation.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_utc_z(value: str) -> bool:
    """True if `value` looks like an ISO-8601 UTC timestamp with a literal
    trailing Z, e.g. "2026-05-25T06:40:00Z".

    Deliberately a cheap, syntactic check (trailing Z, a T separator) and
    not a full ISO-8601 parse: it exists to catch "someone passed a
    datetime's default str() with +00:00" or "someone passed a local time",
    not to validate calendar correctness — `datetime.fromisoformat` already
    owns that job wherever a real datetime is being constructed.
    """
    return isinstance(value, str) and value.endswith("Z") and "T" in value
