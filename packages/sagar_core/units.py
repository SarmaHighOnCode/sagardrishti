"""Explicit unit conversion.

This module exists because of one specific, recurring, hard-to-see bug:
a value in knots reaching code that expects m/s, or degrees reaching code
that expects radians. Neither crashes. Both produce plausible-looking
numbers that are wrong by a constant factor, and in a Lagrangian drift
model a constant velocity error silently corrupts every downstream
attribution result — the plume lands somewhere confident and incorrect.

The convention that prevents it, applied repo-wide:

  1. Every value crossing a module boundary carries its unit in the FIELD
     NAME: `sog_knots`, `speed_ms`, `bearing_deg`, `area_km2`,
     `damping_db`, `slick_age_hours`. Never a bare `speed` or `angle`.
  2. Conversions go through this module, never inline arithmetic. An
     inline `* 0.514` in a drift module is a review rejection — not
     because the constant is wrong, but because it is unreviewable and
     unsearchable when it later turns out to have been applied twice.

Deliberately plain floats rather than a wrapped Quantity type. A units
library (pint and friends) would catch more at runtime, but adds a
dependency this package cannot afford (see the note on why sagar_core
stays dependency-light in __init__.py) and imposes friction on numeric
inner loops in M5. The naming convention plus centralised conversions is
the level of rigour that is actually sustainable here.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# Exact constants. Sourced, not approximated in-line at call sites.
# --------------------------------------------------------------------------

#: One international nautical mile, exactly, by definition.
METRES_PER_NAUTICAL_MILE = 1852.0

#: One knot = one nautical mile per hour, exactly (1852 / 3600).
MS_PER_KNOT = METRES_PER_NAUTICAL_MILE / 3600.0  # 0.5144444...


# --------------------------------------------------------------------------
# Speed
# --------------------------------------------------------------------------


def knots_to_ms(knots: float) -> float:
    """AIS reports speed over ground in knots; drift models work in m/s."""
    return knots * MS_PER_KNOT


def ms_to_knots(ms: float) -> float:
    return ms / MS_PER_KNOT


# --------------------------------------------------------------------------
# Angles
# --------------------------------------------------------------------------


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def rad_to_deg(rad: float) -> float:
    return math.degrees(rad)


def normalise_bearing_deg(deg: float) -> float:
    """Fold any bearing into [0, 360).

    Bearings arrive from AIS (COG), from slick major-axis computation, and
    from wake-direction estimates, and those three sources disagree about
    whether "west" is 270 or -90. Normalise at the boundary so downstream
    comparisons (notably the course-alignment scoring factor) never have
    to care.
    """
    return deg % 360.0


def bearing_difference_deg(a_deg: float, b_deg: float) -> float:
    """Smallest absolute angle between two bearings, in [0, 180].

    Used by the course-alignment factor (docs/SCORING_MODEL.md f2), which
    compares a slick's major-axis bearing against a vessel's COG. Naive
    subtraction gives 350 for headings of 355 and 5, when the real answer
    is 10 — a vessel would look badly misaligned when it is near-perfectly
    aligned.
    """
    diff = abs(normalise_bearing_deg(a_deg) - normalise_bearing_deg(b_deg))
    return min(diff, 360.0 - diff)


# --------------------------------------------------------------------------
# Distance
# --------------------------------------------------------------------------


def nautical_miles_to_metres(nm: float) -> float:
    return nm * METRES_PER_NAUTICAL_MILE


def metres_to_nautical_miles(m: float) -> float:
    return m / METRES_PER_NAUTICAL_MILE


def km_to_metres(km: float) -> float:
    return km * 1000.0


def metres_to_km(m: float) -> float:
    return m / 1000.0


def m2_to_km2(m2: float) -> float:
    """Slick areas are computed in m² by geometry libraries and reported
    in km². The factor is 1e6, not 1e3 — the single most common unit slip
    in area code, and the reason this has a named function."""
    return m2 / 1_000_000.0


def km2_to_m2(km2: float) -> float:
    return km2 * 1_000_000.0


# --------------------------------------------------------------------------
# Decibels
# --------------------------------------------------------------------------


def power_ratio_to_db(ratio: float) -> float:
    """Convert a linear power ratio to decibels: 10·log10(ratio).

    SAR backscatter (σ⁰) is a POWER quantity, so the factor is 10, not 20.
    The 20·log10 form applies to amplitude ratios. Using the wrong one
    doubles every damping figure, which would inflate the damping-ratio
    feature that helps separate mineral oil from biogenic film.

    Raises on ratio <= 0: log10 of a non-positive number is not a quiet
    NaN we want flowing into a detection confidence score.
    """
    if ratio <= 0.0:
        raise ValueError(f"power ratio must be positive to convert to dB, got {ratio}")
    return 10.0 * math.log10(ratio)


def db_to_power_ratio(db: float) -> float:
    return 10.0 ** (db / 10.0)


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------


def seconds_to_hours(seconds: float) -> float:
    return seconds / 3600.0


def hours_to_seconds(hours: float) -> float:
    return hours * 3600.0


def seconds_to_minutes(seconds: float) -> float:
    return seconds / 60.0


def minutes_to_seconds(minutes: float) -> float:
    return minutes * 60.0
