"""Báo cáo ngập của người dân (crowdsourcing) + logic xác nhận."""
from fastapi import APIRouter, HTTPException, Response

from ..db import pool
from ..schemas import ReportClear, ReportCreate

router = APIRouter(prefix="/api/reports", tags=["Báo cáo của người dân"])

# --- Tham số quy tắc xác nhận ---
CONFIRM_RADIUS_M = 100       # bán kính gom các báo cáo gần nhau
CONFIRM_WINDOW_MIN = 15      # chỉ tính báo cáo trong 15 phút gần nhất
CONFIRM_MIN_REPORTS = 3      # đủ 3 báo cáo là xác nhận
SENSOR_MATCH_DEPTH_CM = 5    # cảm biến gần đó đo >= 5 cm thì coi là khớp
SENSOR_FRESH_MIN = 30        # số đo cảm biến phải mới trong 30 phút

# Mức người dân chọn -> độ sâu ước lượng (cm)
LEVEL_DEPTH_CM = {"light": 10, "medium": 25, "heavy": 40}

POINT = "ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography"


@router.post("", status_code=201)
def create_report(body: ReportCreate):
    with pool.connection() as conn:
        rep = conn.execute(
            """INSERT INTO reports (user_id, geom, level, photo_url)
               VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s::report_level, %s)
               RETURNING id, created_at, expires_at""",
            (body.user_id, body.lng, body.lat, body.level, body.photo_url),
        ).fetchone()

        # 1) Các báo cáo còn hiệu lực, gần nhau (kể cả báo cáo vừa gửi)
        nearby = conn.execute(
            f"""SELECT id FROM reports
                WHERE expires_at > now()
                  AND created_at > now() - make_interval(mins => %s)
                  AND ST_DWithin(geom::geography, {POINT}, %s)""",
            (CONFIRM_WINDOW_MIN, body.lng, body.lat, CONFIRM_RADIUS_M),
        ).fetchall()
        nearby_ids = [r["id"] for r in nearby]

        # 2) Có cảm biến gần đó đang đo thấy nước không?
        sensor_match = conn.execute(
            f"""SELECT fp.id FROM flood_points fp
                JOIN LATERAL (
                    SELECT depth_cm, recorded_at FROM water_readings
                    WHERE point_id = fp.id AND source = 'sensor'
                    ORDER BY recorded_at DESC LIMIT 1
                ) r ON TRUE
                WHERE ST_DWithin(fp.geom::geography, {POINT}, %s)
                  AND r.depth_cm >= %s
                  AND r.recorded_at > now() - make_interval(mins => %s)
                LIMIT 1""",
            (body.lng, body.lat, CONFIRM_RADIUS_M, SENSOR_MATCH_DEPTH_CM, SENSOR_FRESH_MIN),
        ).fetchone()

        confirmed = len(nearby_ids) >= CONFIRM_MIN_REPORTS or sensor_match is not None
        if confirmed:
            conn.execute("UPDATE reports SET confirmed = TRUE WHERE id = ANY(%s)", (nearby_ids,))

            # 3) Nếu báo cáo nằm gần một điểm ngập -> ghi thêm số đo nguồn 'crowd'
            point = conn.execute(
                f"""SELECT id FROM flood_points
                    WHERE ST_DWithin(geom::geography, {POINT}, %s)
                    ORDER BY ST_Distance(geom::geography, {POINT}) LIMIT 1""",
                (body.lng, body.lat, CONFIRM_RADIUS_M, body.lng, body.lat),
            ).fetchone()
            if point:
                conn.execute(
                    "INSERT INTO water_readings (point_id, depth_cm, source) VALUES (%s, %s, 'crowd')",
                    (point["id"], LEVEL_DEPTH_CM[body.level]),
                )
            # TODO (Bước 5-6): khoá cạnh đường quanh vị trí này và kích hoạt re-routing

    return {
        "id": rep["id"],
        "level": body.level,
        "confirmed": confirmed,
        "nearby_reports": len(nearby_ids),
        "need_more": 0 if confirmed else CONFIRM_MIN_REPORTS - len(nearby_ids),
        "expires_at": rep["expires_at"],
    }


@router.get("")
def list_reports(only_confirmed: bool = False):
    """Báo cáo còn hiệu lực (GeoJSON). only_confirmed=true để chỉ lấy báo cáo đã xác nhận."""
    sql = """SELECT id, level, confirmed, created_at, expires_at,
                    ST_X(geom) AS lng, ST_Y(geom) AS lat
             FROM reports WHERE expires_at > now()"""
    if only_confirmed:
        sql += " AND confirmed"
    sql += " ORDER BY created_at DESC"

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
                    "level": r["level"],
                    "estimated_depth_cm": LEVEL_DEPTH_CM[r["level"]],
                    "confirmed": r["confirmed"],
                    "created_at": r["created_at"],
                    "expires_at": r["expires_at"],
                },
            }
            for r in rows
        ],
    }


@router.post("/clear")
def clear_reports(body: ReportClear):
    """Người dân báo 'đã hết ngập': hết hạn mọi báo cáo còn hiệu lực trong bán kính 100 m."""
    with pool.connection() as conn:
        rows = conn.execute(
            f"""UPDATE reports SET expires_at = now()
                WHERE expires_at > now()
                  AND ST_DWithin(geom::geography, {POINT}, %s)
                RETURNING id""",
            (body.lng, body.lat, CONFIRM_RADIUS_M),
        ).fetchall()
    return {"cleared": len(rows)}


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int):
    with pool.connection() as conn:
        row = conn.execute("DELETE FROM reports WHERE id = %s RETURNING id", (report_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Không tìm thấy báo cáo id={report_id}")
    return Response(status_code=204)
