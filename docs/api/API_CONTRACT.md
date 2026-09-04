# API Contract

**Status: DRAFT until 15 October 2026, then FROZEN.**

> After the freeze date, breaking changes require the integration lead's sign-off and a version bump. Frontend and backend cannot both be moving in November — see [`ROADMAP.md`](../ROADMAP.md).

Base path `/api/v1`. FastAPI serves live OpenAPI docs at `/docs`.

---

## Conventions

| Rule | Detail |
|---|---|
| Geometry | GeoJSON, WGS84 (EPSG:4326), longitude first |
| Time | ISO 8601 UTC with explicit `Z`. Never a local format |
| Identifiers | String, even when numeric. MMSI is a 9-character string |
| Rasters | Served as COG via TiTiler. **Never as JSON arrays** |
| Pagination | `?limit=` and `?cursor=`. Default 50, max 500 |
| Errors | RFC 7807 problem+json |
| Long jobs | `202 Accepted` with a `job_id`, then poll or subscribe by SSE |

### Uncertainty is mandatory in the schema

Any field representing an inferred quantity carries its uncertainty **in the same object**. This is enforced at the schema level so it cannot be dropped by accident.

```json
{ "slick_age_hours": 7.3, "slick_age_ci": [5.9, 8.8], "confidence": 0.71 }
```

A bare `slick_age_hours` with no interval is a schema violation, not a convenience. Product principle 2.

---

## Endpoints

### Scenes

```
GET    /scenes?bbox=&start=&end=&sensor=      list
GET    /scenes/{scene_id}                     detail + provenance
POST   /scenes/{scene_id}/analyse             -> 202 { job_id }
```

### Detections

```
GET    /detections?scene_id=&min_confidence=  list
GET    /detections/{id}                       polygon, attributes, penalty log
GET    /detections/{id}/suspects              ranked, with factor contributions
GET    /detections/{id}/hindcast              origin probability field (COG URL)
GET    /detections/{id}/forecast?hours=48     forward extent + shoreline impact
GET    /detections/{id}/audit                 the full filter cascade
POST   /detections/{id}/evidence              -> 202 { job_id } -> dossier
```

**`GET /detections/{id}`** returns the rejection reasoning too — this drives the 1:30 demo beat:

```json
{
  "id": "det_01H...",
  "geometry": { "type": "Polygon", "coordinates": [] },
  "confidence": 0.19,
  "confidence_raw": 0.62,
  "classification": "look_alike",
  "attributes": {
    "area_km2": 12.43,
    "major_axis_bearing_deg": 247.3,
    "damping_ratio_db": 8.4,
    "edge_sharpness": 0.31,
    "thickness_class": "sheen"
  },
  "penalties": [
    { "check": "wind_window", "delta": -0.28,
      "reason": "wind speed 1.6 m/s below 2-12 m/s detection window",
      "evidence": { "wind_ms": 1.6, "source": "CMEMS WIND_GLO_PHY_L4" } },
    { "check": "chlorophyll_anomaly", "delta": -0.09,
      "reason": "chlorophyll-a anomaly +2.1 sigma, biogenic film likely" },
    { "check": "recurrence", "delta": -0.06,
      "reason": "dark formation at this location in 4 of last 12 scenes" }
  ]
}
```

**Every penalty carries a human-readable `reason` and machine-readable `evidence`.** The UI renders `reason` directly; the dossier cites `evidence`.

### Suspects

```json
{
  "rank": 1,
  "mmsi": "419001234",
  "imo": "9123221",
  "vessel_name": "MV EXAMPLE CARRIER",
  "vessel_type": "tanker",
  "posterior": 0.71,
  "calibrated": true,
  "inferred_release_utc": "2026-05-25T06:40:00Z",
  "inferred_release_ci_minutes": 50,
  "slick_age_hours": 7.3,
  "slick_age_ci": [5.9, 8.8],
  "factors": [
    { "name": "drift_consistency", "value": 0.81, "weight": 2.5,
      "contribution": 2.14, "confidence": "high" },
    { "name": "course_alignment", "value": 0.94, "weight": 1.4,
      "contribution": 1.87, "confidence": "high" },
    { "name": "ais_gap_anomaly", "value": 0.62, "weight": 1.3,
      "contribution": 1.32, "confidence": "medium",
      "note": "gap 3.1x this vessel's own baseline; good coverage at position" },
    { "name": "off_lane_distance", "value": -0.17, "weight": 0.8,
      "contribution": -0.22, "confidence": "high" }
  ],
  "data_quality": { "records_used": 412, "records_excluded": 7,
                    "exclusion_reasons": { "impossible_speed": 5, "null_island": 2 } }
}
```

Notes that matter:

- **`factors` includes negative contributions.** Exculpatory evidence is never hidden.
- **`ais_gap_anomaly` carries a `note`** explaining what it was measured against — a raw gap duration would be misleading.
- **`data_quality`** reports excluded records. Exclusions never influence the score in either direction.
- **`confidence` per factor** lets the UI grey out factors resting on thin evidence, such as a vessel with no baseline history.

### AIS and ships

```
GET    /ais/tracks?bbox=&start=&end=&mmsi=    interpolated tracks
GET    /ais/vessels/{mmsi}                    static data + baseline gap profile
GET    /ships?scene_id=                       SAR detections
GET    /ships/{id}                            detail incl. dark-vessel flag
```

Dark vessel object:

```json
{
  "id": "shp_01H...",
  "position": { "type": "Point", "coordinates": [74.9033, 12.4821] },
  "dark_vessel": true,
  "size_bucket": "small",
  "size_note": "small radar cross-section; many small craft are AIS-exempt",
  "estimated_length_m": [12, 28],
  "heading_deg": 118.0,
  "ais_match": null
}
```

`size_bucket` is a **soft flag for analyst context**, never a filter. See PRD section 7.6.

### Jobs

```
GET    /jobs/{job_id}                         status, stage, progress
GET    /jobs/{job_id}/events                  SSE stream
```

Stages are **named**, not percentages: `preprocessing`, `detecting`, `filtering`, `hindcasting`, `gating_traffic`, `advecting`, `scoring`, `forecasting`, `building_dossier`.

*"Advecting 50 vessels x 96 release times"* is informative. *"63%"* is not.

---

## Changes after the freeze

1. Raise an issue with the rationale
2. Integration lead approves or rejects
3. Additive changes only where possible — new optional fields, never renamed or removed ones
4. Breaking changes bump to `/api/v2` and both versions run until the frontend migrates

**Additive changes are always allowed.** It is removal and renaming that break a frontend mid-November.
