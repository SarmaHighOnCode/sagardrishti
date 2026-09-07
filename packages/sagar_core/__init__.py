"""sagar_core — shared foundations for the SAGARDRISHTI pipeline.

Depends on nothing in this repo. Everything depends on it.

## Keep this package dependency-light

Only `pydantic` beyond the standard library, and that limit is
deliberate rather than incidental. `sagar_core` needs to be importable
from BOTH runtime environments:

  - `sagar-geo`   (micromamba/conda-forge: GDAL, PROJ, OpenDrift, torch)
  - `sagar-api`   (uv/PyPI: FastAPI, psycopg, redis)

Adding numpy, shapely or xarray here would quietly make the API service
depend on the geospatial stack, which docs/DEVELOPMENT.md §2 splits
apart on purpose. Heavy geometry belongs in the packages that do
geometry (`sagar_sar`, `sagar_drift`), not in the shared base.

The practical payoff: the API can eventually import these types instead
of maintaining a parallel copy — see the note in `types.py` on the
domain/wire split, and on the near-miss where the two nearly drifted
apart on a field name.
"""

from __future__ import annotations

from .config import (
    DEFAULT_GSD_METRES,
    MIN_SAMPLES_FOR_BASELINE,
    TERRESTRIAL_AIS_RANGE_NM,
    WIND_WINDOW_MS,
    Settings,
)
from .geo import (
    CRS_WGS84,
    BBox,
    LonLat,
    haversine_m,
    haversine_nm,
    implied_speed_knots,
    in_bbox,
    initial_bearing_deg,
    validate_lonlat,
)
from .provenance import (
    ProvenanceChain,
    ProvenanceRecord,
    sha256_bytes,
    sha256_config,
    sha256_file,
    utc_now,
)
from .types import (
    Classification,
    DataQuality,
    DataQualitySummary,
    DriftMode,
    DriftRun,
    FactorConfidence,
    Interval,
    Penalty,
    ReleaseTimeEstimate,
    Scene,
    ScoringFactor,
    SlickAgeEstimate,
    SlickAttributes,
    SlickPolygon,
    Suspect,
    ThicknessClass,
)
from .units import (
    bearing_difference_deg,
    db_to_power_ratio,
    knots_to_ms,
    m2_to_km2,
    ms_to_knots,
    normalise_bearing_deg,
    power_ratio_to_db,
)

__all__ = [
    # config
    "Settings",
    "DEFAULT_GSD_METRES",
    "WIND_WINDOW_MS",
    "TERRESTRIAL_AIS_RANGE_NM",
    "MIN_SAMPLES_FOR_BASELINE",
    # geo
    "CRS_WGS84",
    "LonLat",
    "BBox",
    "validate_lonlat",
    "in_bbox",
    "haversine_m",
    "haversine_nm",
    "initial_bearing_deg",
    "implied_speed_knots",
    # units
    "knots_to_ms",
    "ms_to_knots",
    "normalise_bearing_deg",
    "bearing_difference_deg",
    "power_ratio_to_db",
    "db_to_power_ratio",
    "m2_to_km2",
    # provenance
    "ProvenanceRecord",
    "ProvenanceChain",
    "sha256_file",
    "sha256_bytes",
    "sha256_config",
    "utc_now",
    # types
    "Scene",
    "SlickPolygon",
    "SlickAttributes",
    "Penalty",
    "Suspect",
    "ScoringFactor",
    "DataQualitySummary",
    "DriftRun",
    "Interval",
    "SlickAgeEstimate",
    "ReleaseTimeEstimate",
    "Classification",
    "ThicknessClass",
    "DriftMode",
    "FactorConfidence",
    "DataQuality",
]
