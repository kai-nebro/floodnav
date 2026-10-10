-- ============ FloodNav: schema ============
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE vehicle_type   AS ENUM ('motorbike', 'car');
CREATE TYPE reading_source AS ENUM ('sensor', 'crowd', 'ai');
CREATE TYPE report_level   AS ENUM ('light', 'medium', 'heavy');

-- Người dùng
CREATE TABLE users (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    vehicle      vehicle_type NOT NULL DEFAULT 'motorbike',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Điểm ngập ("điểm đen") có gắn cảm biến
CREATE TABLE flood_points (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    geom          geometry(Point, 4326) NOT NULL,
    sensor_id     TEXT UNIQUE,
    threshold_cm  INT NOT NULL DEFAULT 20,       -- ngưỡng nguy hiểm cho xe máy
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_flood_points_geom ON flood_points USING GIST (geom);

-- Chuỗi thời gian mực nước (từ cảm biến / người dân / AI)
CREATE TABLE water_readings (
    id           BIGSERIAL PRIMARY KEY,
    point_id     INT NOT NULL REFERENCES flood_points(id) ON DELETE CASCADE,
    depth_cm     NUMERIC(6,1) NOT NULL CHECK (depth_cm >= 0),
    source       reading_source NOT NULL DEFAULT 'sensor',
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_readings_point_time ON water_readings (point_id, recorded_at DESC);

-- Báo cáo của người dân (crowdsourcing)
CREATE TABLE reports (
    id           SERIAL PRIMARY KEY,
    user_id      INT REFERENCES users(id) ON DELETE SET NULL,
    geom         geometry(Point, 4326) NOT NULL,
    level        report_level NOT NULL,
    photo_url    TEXT,
    confirmed    BOOLEAN NOT NULL DEFAULT FALSE,  -- true khi đủ >=3 báo cáo gần nhau hoặc khớp cảm biến
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '45 minutes'
);
CREATE INDEX idx_reports_geom ON reports USING GIST (geom);
CREATE INDEX idx_reports_expires ON reports (expires_at);

-- Dự báo AI
CREATE TABLE predictions (
    id                   BIGSERIAL PRIMARY KEY,
    point_id             INT NOT NULL REFERENCES flood_points(id) ON DELETE CASCADE,
    predicted_depth_cm   NUMERIC(6,1) NOT NULL,
    horizon_min          INT NOT NULL CHECK (horizon_min IN (30, 60)),
    risk_score           NUMERIC(4,3) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_predictions_point_time ON predictions (point_id, created_at DESC);

-- Phiên dẫn đường đang hoạt động (để re-routing)
CREATE TABLE nav_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       INT REFERENCES users(id) ON DELETE CASCADE,
    vehicle       vehicle_type NOT NULL DEFAULT 'motorbike',
    current_pos   geometry(Point, 4326),
    destination   geometry(Point, 4326) NOT NULL,
    route_edges   BIGINT[] NOT NULL DEFAULT '{}',  -- id các cạnh (OSM edge) còn lại của lộ trình
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_nav_active ON nav_sessions (active) WHERE active;
