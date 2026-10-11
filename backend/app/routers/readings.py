"""Số đo mực nước (water_readings) – cảm biến gửi lên đây."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import pool
from ..schemas import ReadingCreate

router = APIRouter(prefix="/api/readings", tags=["Số đo mực nước"])


@router.post("", status_code=201)
def create_reading(body: ReadingCreate):
    """Cảm biến (hoặc script giả lập) gửi mực nước. Có thể dùng point_id hoặc sensor_id."""
    with pool.connection() as conn:
        if body.point_id is not None:
            point = conn.execute(
                "SELECT id, threshold_cm FROM flood_points WHERE id = %s", (body.point_id,)
            ).fetchone()
        else:
            point = conn.execute(
                "SELECT id, threshold_cm FROM flood_points WHERE sensor_id = %s", (body.sensor_id,)
            ).fetchone()
        if point is None:
            raise HTTPException(404, "Không tìm thấy điểm ngập tương ứng")

        row = conn.execute(
            """INSERT INTO water_readings (point_id, depth_cm, source)
               VALUES (%s, %s, %s::reading_source)
               RETURNING id, point_id, depth_cm, source, recorded_at""",
            (point["id"], body.depth_cm, body.source),
        ).fetchone()

    row["depth_cm"] = float(row["depth_cm"])
    row["exceeds_threshold"] = row["depth_cm"] >= point["threshold_cm"]
    # TODO (Bước 5-6): nếu exceeds_threshold -> khoá cạnh đường và kích hoạt re-routing
    return row


@router.get("")
def list_readings(
    point_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Lịch sử số đo, mới nhất trước. Lọc theo point_id nếu cần."""
    sql = "SELECT id, point_id, depth_cm, source, recorded_at FROM water_readings"
    params: list = []
    if point_id is not None:
        sql += " WHERE point_id = %s"
        params.append(point_id)
    sql += " ORDER BY recorded_at DESC LIMIT %s"
    params.append(limit)

    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    for r in rows:
        r["depth_cm"] = float(r["depth_cm"])
    return rows
