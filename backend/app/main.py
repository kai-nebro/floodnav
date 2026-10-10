from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import pool

app = FastAPI(title="FloodNav API", version="0.1.0")

# Cho phép frontend (React) gọi API khi dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Kiểm tra backend + DB + PostGIS đã sống chưa."""
    with pool.connection() as conn:
        row = conn.execute("SELECT PostGIS_Version() AS postgis").fetchone()
    return {"status": "ok", "postgis": row["postgis"]}


@app.get("/api/flood-points")
def list_flood_points():
    """Trả về GeoJSON FeatureCollection, kèm mực nước mới nhất của mỗi điểm."""
    sql = """
        SELECT fp.id, fp.name, fp.sensor_id, fp.threshold_cm,
               ST_X(fp.geom) AS lng, ST_Y(fp.geom) AS lat,
               COALESCE(r.depth_cm, 0) AS depth_cm
        FROM flood_points fp
        LEFT JOIN LATERAL (
            SELECT depth_cm FROM water_readings
            WHERE point_id = fp.id
            ORDER BY recorded_at DESC LIMIT 1
        ) r ON TRUE
        ORDER BY fp.id
    """
    with pool.connection() as conn:
        rows = conn.execute(sql).fetchall()

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
                "properties": {
                    "id": r["id"],
                    "name": r["name"],
                    "sensor_id": r["sensor_id"],
                    "threshold_cm": r["threshold_cm"],
                    "depth_cm": float(r["depth_cm"]),
                },
            }
            for r in rows
        ],
    }
