"""
============================ SYNTHETIC ============================
In-memory fixture data backing every endpoint below until the real
pipeline (M1-M7) and a live database exist. None of this is a real
detection or a real vessel.

Deliberately kept identifier-for-identifier consistent with
web/src/lib/fixtures.ts (same scene id, same detection ids, same MMSIs,
same confidence/factor numbers) so that swapping the console from its
local fixtures to a real fetch against this API changes nothing about
what the demo looks like. If you change a value on one side, change it
on the other, or the two fixture sets will quietly drift apart and the
"day the API goes live" swap will look like a regression.
=====================================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .format import format_utc
from .schemas import (
    AisTrack,
    AisTrackPoint,
    BaselineGapProfile,
    DataQualitySummary,
    Detection,
    DetectionAttributes,
    GeoPoint,
    GeoPolygon,
    Penalty,
    Scene,
    ShipDetection,
    Suspect,
    SuspectFactor,
    VesselStatic,
)

SCENE_ID = "S1C_IW_GRDH_1SDV_20260525T064012"

SCENE = Scene(
    id=SCENE_ID,
    sensor="Sentinel-1C",
    acquired_utc="2026-05-25T06:40:12Z",
    footprint=GeoPolygon(
        coordinates=[
            [
                (75.0, 9.4),
                (76.2, 9.4),
                (76.2, 10.3),
                (75.0, 10.3),
                (75.0, 9.4),
            ]
        ]
    ),
    product_hash="a3f9c2e1b7d4a8f012",
    status="analysed",
)

# Confirmed slick — matches web/src/lib/fixtures.ts SAMPLE_SLICKS[0].
DETECTION_OIL = Detection(
    id="det_synthetic_001",
    scene_id=SCENE_ID,
    geometry=GeoPolygon(
        coordinates=[
            [
                (75.42, 9.88),
                (75.61, 9.79),
                (75.74, 9.68),
                (75.70, 9.62),
                (75.55, 9.71),
                (75.38, 9.83),
                (75.42, 9.88),
            ]
        ]
    ),
    confidence=0.81,
    confidence_raw=0.81,
    classification="oil",
    attributes=DetectionAttributes(
        area_km2=12.43,
        major_axis_bearing_deg=247.3,
        damping_ratio_db=8.4,
        edge_sharpness=0.74,
        thickness_class="sheen",
    ),
    penalties=[],
)

# Rejected look-alike — matches SAMPLE_SLICKS[1] AND the contract's own
# worked example in API_CONTRACT.md's "GET /detections/{id}" section.
DETECTION_LOOKALIKE = Detection(
    id="det_synthetic_002",
    scene_id=SCENE_ID,
    geometry=GeoPolygon(
        coordinates=[
            [
                (75.90, 10.05),
                (76.05, 10.02),
                (76.08, 9.94),
                (75.92, 9.96),
                (75.90, 10.05),
            ]
        ]
    ),
    confidence=0.19,
    confidence_raw=0.62,
    classification="look_alike",
    attributes=DetectionAttributes(
        area_km2=5.10,
        major_axis_bearing_deg=103.0,
        damping_ratio_db=3.1,
        edge_sharpness=0.22,
        thickness_class="sheen",
    ),
    penalties=[
        Penalty(
            check="wind_window",
            delta=-0.28,
            reason="wind speed 1.6 m/s below 2-12 m/s detection window",
            evidence={"wind_ms": 1.6, "source": "CMEMS WIND_GLO_PHY_L4"},
        ),
        Penalty(
            check="chlorophyll_anomaly",
            delta=-0.09,
            reason="chlorophyll-a anomaly +2.1 sigma, biogenic film likely",
        ),
        Penalty(
            check="recurrence",
            delta=-0.06,
            reason="dark formation at this location in 4 of last 12 scenes",
        ),
    ],
)

DETECTIONS: dict[str, Detection] = {
    DETECTION_OIL.id: DETECTION_OIL,
    DETECTION_LOOKALIKE.id: DETECTION_LOOKALIKE,
}

# The filter cascade audit example from PRD §8.4 / DESIGN_SYSTEM §6.4:
# 214 candidate vessels down to 7, every drop reason logged.
AUDIT_TRAIL = {
    "detection_id": DETECTION_OIL.id,
    "stages": [
        {"stage": "reachability_gate", "before": 214, "after": 46, "dropped": 168},
        {"stage": "timing_gate", "before": 46, "after": 19, "dropped": 27},
        {"stage": "kinematic_plausibility", "before": 19, "after": 11, "dropped": 8},
        {"stage": "drift_score_floor", "before": 11, "after": 7, "dropped": 4},
    ],
    "final_candidate_count": 7,
}

# Suspects — matches SAMPLE_TRACKS mmsi/rank/posterior in the console
# fixtures, and reproduces the contract's own worked suspect example
# verbatim for MMSI 419001234.
SUSPECT_1 = Suspect(
    rank=1,
    mmsi="419001234",
    imo="9123221",
    vessel_name="SYNTHETIC VESSEL A",
    vessel_type="tanker",
    posterior=0.71,
    calibrated=True,
    inferred_release_utc="2026-05-25T06:40:00Z",
    inferred_release_ci_minutes=50,
    slick_age_hours=7.3,
    slick_age_ci=(5.9, 8.8),
    factors=[
        SuspectFactor(
            name="drift_consistency", value=0.81, weight=2.5, contribution=2.14, confidence="high"
        ),
        SuspectFactor(
            name="course_alignment", value=0.94, weight=1.4, contribution=1.87, confidence="high"
        ),
        SuspectFactor(
            name="ais_gap_anomaly",
            value=0.62,
            weight=1.3,
            contribution=1.32,
            confidence="medium",
            note="gap 3.1x this vessel's own baseline; good coverage at position",
        ),
        SuspectFactor(
            name="speed_anomaly", value=0.68, weight=1.1, contribution=0.94, confidence="high"
        ),
        SuspectFactor(
            name="night_time_release",
            value=1.0,
            weight=0.5,
            contribution=0.41,
            confidence="high",
        ),
        SuspectFactor(
            # Negative contribution — exculpatory, and never hidden.
            name="off_lane_distance",
            value=-0.17,
            weight=0.8,
            contribution=-0.22,
            confidence="high",
        ),
    ],
    data_quality=DataQualitySummary(
        records_used=412,
        records_excluded=7,
        exclusion_reasons={"impossible_speed": 5, "null_island": 2},
    ),
)

SUSPECT_2 = Suspect(
    rank=2,
    mmsi="563889000",
    imo=None,
    vessel_name="SYNTHETIC VESSEL B",
    vessel_type="container",
    posterior=0.44,
    calibrated=True,
    inferred_release_utc="2026-05-25T05:55:00Z",
    inferred_release_ci_minutes=70,
    slick_age_hours=8.1,
    slick_age_ci=(6.2, 10.4),
    factors=[
        SuspectFactor(
            name="drift_consistency", value=0.52, weight=2.5, contribution=1.30, confidence="medium"
        ),
        SuspectFactor(
            name="course_alignment", value=0.61, weight=1.4, contribution=0.85, confidence="medium"
        ),
        SuspectFactor(
            name="ais_gap_anomaly",
            value=0.10,
            weight=1.3,
            contribution=0.13,
            confidence="low",
            note=(
                "vessel has under 2 weeks of recorded history — baseline "
                "is a class prior, not this vessel's own"
            ),
        ),
    ],
    data_quality=DataQualitySummary(
        records_used=58, records_excluded=1, exclusion_reasons={"null_island": 1}
    ),
)

SUSPECTS_BY_DETECTION: dict[str, list[Suspect]] = {
    DETECTION_OIL.id: [SUSPECT_1, SUSPECT_2],
}

# AIS tracks — SYNTHETIC VESSEL A's approach, matching SAMPLE_TRACKS[0]'s
# path in the console fixtures.
_TRACK_A_PATH = [
    (75.10, 10.30),
    (75.30, 10.12),
    (75.48, 9.98),
    (75.66, 9.84),
    (75.88, 9.70),
]

AIS_TRACKS: dict[str, AisTrack] = {
    "419001234": AisTrack(
        mmsi="419001234",
        vessel_name="SYNTHETIC VESSEL A",
        points=[
            AisTrackPoint(
                # 40-minute reporting interval, ending at the scene's
                # acquisition time — a plausible transit up to T_sar.
                time_utc=format_utc(datetime(2026, 5, 25, 4, 0, 0) + timedelta(minutes=40 * i)),
                lat=lat,
                lon=lon,
                sog_knots=11.2,
                cog_degrees=247.0,
                data_quality="ok",
            )
            for i, (lon, lat) in enumerate(_TRACK_A_PATH)
        ],
    ),
}

VESSELS: dict[str, VesselStatic] = {
    "419001234": VesselStatic(
        mmsi="419001234",
        imo="9123221",
        vessel_name="SYNTHETIC VESSEL A",
        vessel_type="tanker",
        baseline_gap_profile=BaselineGapProfile(
            sample_count=3120,
            median_gap_seconds=240.0,
            p95_gap_seconds=1320.0,
            stale=False,
            has_sufficient_history=True,
        ),
    ),
    "563889000": VesselStatic(
        mmsi="563889000",
        imo=None,
        vessel_name="SYNTHETIC VESSEL B",
        vessel_type="container",
        # Under two weeks of history, below MIN_SAMPLES_FOR_BASELINE —
        # matches SUSPECT_2's low-confidence ais_gap_anomaly note above.
        # See SCORING_MODEL.md §5.
        baseline_gap_profile=BaselineGapProfile(
            sample_count=140,
            median_gap_seconds=360.0,
            p95_gap_seconds=1860.0,
            stale=False,
            has_sufficient_history=False,
        ),
    ),
}

# Ships — matches SAMPLE_SHIPS in the console fixtures exactly.
SHIPS: dict[str, ShipDetection] = {
    "shp_1": ShipDetection(
        id="shp_1",
        position=GeoPoint(coordinates=(75.66, 9.84)),
        dark_vessel=False,
        size_bucket="large",
        size_note="AIS-correlated",
        estimated_length_m=(180.0, 210.0),
        heading_deg=247.0,
        ais_match="419001234",
    ),
    "shp_2": ShipDetection(
        id="shp_2",
        position=GeoPoint(coordinates=(75.50, 10.02)),
        dark_vessel=False,
        size_bucket="medium",
        size_note="AIS-correlated",
        estimated_length_m=(90.0, 120.0),
        heading_deg=190.0,
        ais_match="563889000",
    ),
    "shp_3": ShipDetection(
        id="shp_3",
        position=GeoPoint(coordinates=(75.82, 9.55)),
        dark_vessel=True,
        size_bucket="small",
        size_note="small radar cross-section; many small craft are AIS-exempt",
        estimated_length_m=(12.0, 28.0),
        heading_deg=118.0,
        ais_match=None,
    ),
}
