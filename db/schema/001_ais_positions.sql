-- 0001_ais_positions.sql
-- AIS data plane tables. Written by services/aisd (Go), read by everything
-- else (Python). See docs/adr/0005-go-for-the-ais-data-plane.md.
--
-- Forward-only. Do not edit after it has shipped to any environment -
-- add a new numbered migration instead.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Millions of rows, queried almost exclusively as "positions in this bbox
-- during this window" - the textbook hypertable case. See db/README.md.
CREATE TABLE IF NOT EXISTS ais_positions (
    time            TIMESTAMPTZ      NOT NULL,
    mmsi            BIGINT           NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    -- Generated rather than written directly: aisd COPYs plain lat/lon
    -- floats (a type pgx's binary COPY protocol supports natively) and
    -- Postgres derives the PostGIS point, so the Go side never has to
    -- speak PostGIS's WKB wire format.
    position        GEOMETRY(Point, 4326)
                    GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,
    sog_knots       REAL,
    cog_degrees     REAL,
    true_heading    SMALLINT,
    nav_status      SMALLINT,
    rate_of_turn    REAL,
    aoi             TEXT             NOT NULL,       -- 'arabian_sea' | 'bay_of_bengal'
    source          TEXT             NOT NULL DEFAULT 'aisstream',
    data_quality    TEXT             NOT NULL DEFAULT 'ok',  -- 'ok' | 'unreliable'
    quality_reason  TEXT,                                     -- populated when data_quality = 'unreliable'
    recorded_at     TIMESTAMPTZ      NOT NULL DEFAULT now(),  -- when aisd persisted it
    PRIMARY KEY (mmsi, time)
);

SELECT create_hypertable(
    'ais_positions', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS ais_positions_mmsi_time_idx ON ais_positions (mmsi, time DESC);
CREATE INDEX IF NOT EXISTS ais_positions_position_gist  ON ais_positions USING GIST (position);
CREATE INDEX IF NOT EXISTS ais_positions_aoi_time_idx   ON ais_positions (aoi, time DESC);

-- data_quality flags rows failing the pre-filter (MMSI 0, position at
-- (0,0), impossible implied speed, garbled static). Marked, never deleted -
-- they stay auditable and scoring queries must exclude them explicitly.
-- Never silently drop a row here; the AIS feed has no replay.

-- Type 5 / 24 static and voyage data. Latest-per-MMSI view backs the
-- "who is this vessel" lookup the attribution engine needs.
CREATE TABLE IF NOT EXISTS ais_static (
    time            TIMESTAMPTZ      NOT NULL,
    mmsi            BIGINT           NOT NULL,
    imo             BIGINT,
    call_sign       TEXT,
    ship_name       TEXT,
    ship_type       SMALLINT,
    dim_bow         REAL,
    dim_stern       REAL,
    dim_port        REAL,
    dim_starboard   REAL,
    destination     TEXT,
    source          TEXT             NOT NULL DEFAULT 'aisstream',
    recorded_at     TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (mmsi, time)
);

CREATE INDEX IF NOT EXISTS ais_static_mmsi_time_idx ON ais_static (mmsi, time DESC);

CREATE OR REPLACE VIEW ais_static_latest AS
    SELECT DISTINCT ON (mmsi) *
    FROM ais_static
    ORDER BY mmsi, time DESC;

-- Per-vessel normal gap behaviour, refreshed on a schedule. Backs the
-- gap-anomaly scoring factor - see docs/SCORING_MODEL.md section 2.1.
-- Populated by a Python job in Phase 1; the table exists from day one so
-- aisd's schema and the scoring model's schema never drift apart.
CREATE TABLE IF NOT EXISTS ais_baseline_profiles (
    mmsi                BIGINT PRIMARY KEY,
    median_gap_seconds  REAL,
    p95_gap_seconds     REAL,
    sample_count        INTEGER NOT NULL DEFAULT 0,
    stale               BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
