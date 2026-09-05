-- 0002_core_pipeline.sql
-- Scenes, detections and everything M1-M7 attach to them: the tables
-- ais_positions/ais_static/ais_baseline_profiles (0001) don't cover.
-- See docs/ARCHITECTURE.md section 5 for the full storage design this
-- follows, and services/api/app/schemas.py for the Pydantic shapes these
-- columns are meant to mirror closely enough that swapping a fixture for
-- a real query is close to a drop-in replacement, not a redesign.
--
-- Forward-only. Do not edit after it has shipped to any environment -
-- add a new numbered migration instead.
--
-- Nothing in this pipeline exists yet (M1-M7 are unwritten - see
-- docs/ROADMAP.md). These tables exist now for the same reason
-- ais_baseline_profiles did in 0001: so the schema and the API contract
-- (docs/api/API_CONTRACT.md, frozen 15 Oct) never have to be designed
-- twice, and so nobody building M1-M7 has to also invent a schema.

-- postgis/timescaledb already created in 0001 - not re-declared here.
-- Migrations apply in order; this one depends on 0001 having run.

-- --------------------------------------------------------------------
-- Identifiers: app-generated, string, type-prefixed (det_..., shp_...,
-- job_..., drift_...). Not SERIAL/UUID - matches the style already used
-- in docs/api/API_CONTRACT.md's own worked examples ("det_01H...",
-- "shp_01H..."). TEXT throughout for these, not BIGINT/UUID.
-- --------------------------------------------------------------------

-- One row per ingested SAR (or eventually NISAR) product. id is the
-- product's own identifier (e.g. "S1C_IW_GRDH_1SDV_20260525T064012"),
-- not a synthetic key - it is already globally unique and human-legible,
-- and every log line and dossier page wants to print it as-is.
CREATE TABLE IF NOT EXISTS scenes (
    id              TEXT             PRIMARY KEY,
    sensor          TEXT             NOT NULL,          -- 'Sentinel-1C', 'Sentinel-1D', ...
    acquired_at     TIMESTAMPTZ      NOT NULL,
    footprint       GEOMETRY(Polygon, 4326) NOT NULL,
    product_hash    TEXT             NOT NULL,          -- sha256, for the evidence dossier's provenance page
    status          TEXT             NOT NULL DEFAULT 'ingested',  -- 'ingested' | 'preprocessing' | 'analysed'
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scenes_acquired_at_idx  ON scenes (acquired_at DESC);
CREATE INDEX IF NOT EXISTS scenes_footprint_gist   ON scenes USING GIST (footprint);

-- M2 output. penalties is the itemised Stage C reasoning ("confidence
-- reduced 0.62 -> 0.19: wind speed 1.6 m/s below detection window ...")
-- - the single cheapest credibility feature in the whole product
-- (docs/DESIGN_SYSTEM.md section 6.3), so it is stored in full, not
-- summarised. JSONB matches Penalty in schemas.py exactly:
--   [{"check": str, "delta": float, "reason": str, "evidence": {...}|null}, ...]
CREATE TABLE IF NOT EXISTS detections (
    id              TEXT             PRIMARY KEY,
    scene_id        TEXT             NOT NULL REFERENCES scenes(id),
    geometry        GEOMETRY(Polygon, 4326) NOT NULL,
    confidence      REAL             NOT NULL,
    confidence_raw  REAL             NOT NULL,          -- pre-Stage-C value; struck through in the UI, never hidden
    classification  TEXT             NOT NULL,          -- 'oil' | 'look_alike'
    penalties       JSONB            NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS detections_scene_id_idx    ON detections (scene_id);
CREATE INDEX IF NOT EXISTS detections_confidence_idx  ON detections (confidence DESC);
CREATE INDEX IF NOT EXISTS detections_geometry_gist   ON detections USING GIST (geometry);

-- M3 output. Split from `detections` 1:1 rather than inlined - M2 (Stage
-- A/B/C) and M3 (characterisation) are separate pipeline stages owned by
-- the same person but run as separate steps, and a detection can exist
-- (geometry + confidence known) before its full geometric
-- characterisation has been computed.
CREATE TABLE IF NOT EXISTS detection_attributes (
    detection_id            TEXT   PRIMARY KEY REFERENCES detections(id),
    area_km2                 REAL   NOT NULL,
    major_axis_bearing_deg   REAL   NOT NULL,
    damping_ratio_db         REAL   NOT NULL,
    edge_sharpness           REAL   NOT NULL,
    thickness_class          TEXT   NOT NULL             -- 'sheen' | 'thick_film' - see schemas.py's own
                                                          -- comment: provisional pending a formal M3 taxonomy
);

-- M4 output. ais_match is a plain MMSI, not a foreign key into
-- ais_static/ais_positions: MMSI is neither stable nor unique in the
-- wild (spoofing, reuse - see docs/SCORING_MODEL.md section 2.1 and
-- ADR context on AIS data quality), so treating it as a hard-linked key
-- here would assert a guarantee the data itself does not honour.
CREATE TABLE IF NOT EXISTS ship_detections (
    id                      TEXT     PRIMARY KEY,
    scene_id                TEXT     NOT NULL REFERENCES scenes(id),
    position                GEOMETRY(Point, 4326) NOT NULL,
    dark_vessel             BOOLEAN  NOT NULL,
    -- Soft flag for analyst context ONLY - PRD section 7.6. Never use
    -- this column to filter dark_vessel results in a query; many small
    -- craft are legally AIS-exempt and are not evaders.
    size_bucket             TEXT     NOT NULL,           -- 'small' | 'medium' | 'large'
    size_note               TEXT     NOT NULL,
    estimated_length_min_m  REAL,
    estimated_length_max_m  REAL,
    heading_deg             REAL,
    ais_match               BIGINT,                      -- MMSI, or NULL when genuinely dark. No FK - see above.
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ship_detections_scene_id_idx   ON ship_detections (scene_id);
CREATE INDEX IF NOT EXISTS ship_detections_dark_idx       ON ship_detections (dark_vessel) WHERE dark_vessel;
CREATE INDEX IF NOT EXISTS ship_detections_position_gist  ON ship_detections USING GIST (position);

-- M5 output. One row per ensemble run - backward hindcast, forward
-- forecast, or the per-vessel attribution run (ADR 0001). config and
-- forcing_versions are stored as JSONB rather than normalised columns
-- because the ensemble parameter set (wind drift factor range, current
-- product choice, diffusivity, particle/member counts, ...) is exactly
-- the kind of thing that grows as M5 matures, and every field in both
-- blobs belongs on the evidence dossier's provenance page verbatim.
--
-- Large per-particle output (drift_particles - see ARCHITECTURE.md
-- section 5) is deliberately NOT a table here: "hypertable or Parquet,
-- Parquet on the object store if row counts get uncomfortable" is an M5
-- implementation decision, not a schema decision to make speculatively
-- before the ensemble code exists. Add it in a migration once M5 is
-- being built and the actual row-count shape is known.
CREATE TABLE IF NOT EXISTS drift_runs (
    id                  TEXT        PRIMARY KEY,
    detection_id        TEXT        NOT NULL REFERENCES detections(id),
    mode                TEXT        NOT NULL,      -- 'backward' | 'forward' | 'per_vessel'
    config              JSONB       NOT NULL,       -- ensemble member count, perturbation ranges, ...
    forcing_versions    JSONB       NOT NULL,       -- CMEMS/ERA5/GEBCO product IDs and versions used
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS drift_runs_detection_id_idx ON drift_runs (detection_id);
CREATE INDEX IF NOT EXISTS drift_runs_mode_idx         ON drift_runs (mode);

-- M6 output. (detection_id, mmsi) is the natural key - a vessel-in-a-
-- suspect-list is what has identity here, not an arbitrary row id.
-- `rank` is stored (denormalised) rather than derived purely from
-- `posterior` at query time, because a recalibration could in principle
-- reorder ranks without every consumer wanting to recompute that order
-- itself.
--
-- factors is JSONB matching SuspectFactor in schemas.py exactly:
--   [{"name","value","weight","contribution","confidence","note"}, ...]
-- Every factor is stored, including negative (exculpatory) ones -
-- SCORING_MODEL.md section 7 is explicit that these are never hidden,
-- and that is a data-modelling constraint, not just a UI choice: there
-- is no "hidden factors" column to (mis)use.
CREATE TABLE IF NOT EXISTS suspects (
    detection_id                    TEXT    NOT NULL REFERENCES detections(id),
    mmsi                             BIGINT  NOT NULL,
    rank                             SMALLINT NOT NULL,
    imo                              BIGINT,
    vessel_name                      TEXT,
    vessel_type                      TEXT,
    posterior                        REAL    NOT NULL,
    calibrated                       BOOLEAN NOT NULL,
    inferred_release_at              TIMESTAMPTZ NOT NULL,
    inferred_release_ci_minutes      REAL    NOT NULL,
    slick_age_hours                  REAL    NOT NULL,
    slick_age_ci_lo_hours            REAL    NOT NULL,
    slick_age_ci_hi_hours            REAL    NOT NULL,
    factors                          JSONB   NOT NULL,
    data_quality_records_used        INTEGER NOT NULL,
    data_quality_records_excluded    INTEGER NOT NULL,
    data_quality_exclusion_reasons   JSONB   NOT NULL DEFAULT '{}',
    PRIMARY KEY (detection_id, mmsi)
);

CREATE INDEX IF NOT EXISTS suspects_detection_rank_idx ON suspects (detection_id, rank);

-- M7 output. id, not detection_id, is the primary key: a dossier can be
-- regenerated (recalibrated weights, corrected input) and the prior
-- version is kept rather than overwritten - "chain of custody" is the
-- whole point of this table (docs/PRD.md section 1, "Explainable over
-- accurate" and the dossier's provenance page). is_current marks which
-- one a plain "get me the dossier for this detection" lookup should
-- return; superseded dossiers stay queryable by id for audit.
CREATE TABLE IF NOT EXISTS evidence_dossiers (
    id              TEXT        PRIMARY KEY,
    detection_id    TEXT        NOT NULL REFERENCES detections(id),
    manifest        JSONB       NOT NULL,     -- source hashes, model/weights hashes, config snapshot
    signature       TEXT        NOT NULL,     -- hash chain signature over the manifest
    pdf_path        TEXT        NOT NULL,     -- object store path/key, not raster bytes in the DB
    is_current      BOOLEAN     NOT NULL DEFAULT TRUE,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS evidence_dossiers_detection_id_idx ON evidence_dossiers (detection_id);
-- At most one CURRENT dossier per detection; any number of superseded ones.
CREATE UNIQUE INDEX IF NOT EXISTS evidence_dossiers_one_current_idx
    ON evidence_dossiers (detection_id) WHERE is_current;

-- ARQ job state mirror for the UI (docs/api/API_CONTRACT.md's
-- GET /jobs/{id} and /jobs/{id}/events). Redis/ARQ owns actual queue
-- state and retry semantics; this table is what the API reads so a
-- browser refresh doesn't need to reopen an SSE connection into ARQ
-- internals. stage is one of the NAMED stages the contract requires
-- ("preprocessing" ... "building_dossier"), never a percentage - see
-- docs/api/API_CONTRACT.md's own reasoning for why.
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT        PRIMARY KEY,
    kind            TEXT        NOT NULL,      -- 'analyse' | 'evidence'
    scene_id        TEXT        REFERENCES scenes(id),
    detection_id    TEXT        REFERENCES detections(id),
    status          TEXT        NOT NULL DEFAULT 'queued',  -- 'queued'|'running'|'done'|'failed'
    stage           TEXT,                       -- named stage - see module comment above
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
