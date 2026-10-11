"""CRUD điểm ngập (flood_points)."""
import psycopg
from fastapi import APIRouter, HTTPException, Response

from ..db import pool
from ..schemas import FloodPointCreate, FloodPointUpdate

router = APIRouter(prefix="/api/flood-points", tags=["Điểm ngập"])

SELECT_SQL = """
    SELECT fp.id, fp.name, fp.sensor_id, fp.threshold_cm,
           ST_X(fp.geom) AS lng, ST_Y(fp.geom) AS lat,
           COALESCE(r.depth_cm, 0) AS depth_cm,
           r.recorded_at AS last_reading_at
    FROM flood_points fp
    LEFT JOIN LATERAL (
        SELECT depth_cm, recorded_at FROM water_readings
        WHERE point_id = fp.id
        ORDER BY recorded_at DESC LIMIT 1
    ) r ON TRUE
"""


def _status(depth: float, threshold: int) -> str:
    if depth < 5:
        return "safe"        # an toàn
    if depth < threshold:
        return "warning"     # ngập nhẹ, đi được nhưng cẩn thận
    return "danger"          # vượt ngưỡng, sẽ bị chặn khi tìm đường


def _to_feature(r: dict) -> dict:
    depth = float(r["depth_cm"])
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
        "properties": {
            "id": r["id"],
            "name": r["name"],
            "sensor_id": r["sensor_id"],
            "threshold_cm": r["threshold_cm"],
            "depth_cm": depth,
            "status": _status(depth, r["threshold_cm"]),
            "last_reading_at": r["last_reading_at"],
        },
    }


def _get_or_404(point_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(SELECT_SQL + " WHERE fp.id = %s", (point_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Không tìm thấy điểm ngập id={point_id}")
    return _to_feature(row)


@router.get("")
def list_flood_points():
    """Danh sách điểm ngập (GeoJSON) kèm mực nước mới nhất."""
    with pool.connection() as conn:
        rows = conn.execute(SELECT_SQL + " ORDER BY fp.id").fetchall()
    return {"type": "FeatureCollection", "features": [_to_feature(r) for r in rows]}


@router.get("/{point_id}")
def get_flood_point(point_id: int):
    return _get_or_404(point_id)


@router.post("", status_code=201)
def create_flood_point(body: FloodPointCreate):
    try:
        with pool.connection() as conn:
            new_id = conn.execute(
                """INSERT INTO flood_points (name, geom, sensor_id, threshold_cm)
                   VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                   RETURNING id""",
                (body.name, body.lng, body.lat, body.sensor_id or None, body.threshold_cm),
            ).fetchone()["id"]
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, f"sensor_id '{body.sensor_id}' đã được dùng cho điểm khác")
    return _get_or_404(new_id)


@router.put("/{point_id}")
def update_flood_point(point_id: int, body: FloodPointUpdate):
    """Cập nhật một phần: chỉ các trường được gửi lên mới bị đổi."""
    params = {
        "id": point_id,
        "name": body.name,
        "sensor_id": body.sensor_id,
        "threshold": body.threshold_cm,
        "lng": body.lng,
        "lat": body.lat,
    }
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """UPDATE flood_points SET
                       name         = COALESCE(%(name)s::text, name),
                       sensor_id    = COALESCE(%(sensor_id)s::text, sensor_id),
                       threshold_cm = COALESCE(%(threshold)s::int, threshold_cm),
                       geom = CASE WHEN %(lng)s::float8 IS NULL THEN geom
                                   ELSE ST_SetSRID(ST_MakePoint(%(lng)s::float8, %(lat)s::float8), 4326) END
                   WHERE id = %(id)s
                   RETURNING id""",
                params,
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, f"sensor_id '{body.sensor_id}' đã được dùng cho điểm khác")
    if row is None:
        raise HTTPException(404, f"Không tìm thấy điểm ngập id={point_id}")
    return _get_or_404(point_id)


@router.delete("/{point_id}", status_code=204)
def delete_flood_point(point_id: int):
    with pool.connection() as conn:
        row = conn.execute(
            "DELETE FROM flood_points WHERE id = %s RETURNING id", (point_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"Không tìm thấy điểm ngập id={point_id}")
    return Response(status_code=204)
