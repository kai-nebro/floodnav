from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import pool
from .routers import flood_points, graph_info, readings, reports, route

app = FastAPI(title="FloodNav API", version="0.3.0")

# Cho phép frontend (React) gọi API khi dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flood_points.router)
app.include_router(readings.router)
app.include_router(reports.router)
app.include_router(graph_info.router)
app.include_router(route.router)


@app.get("/api/health", tags=["Hệ thống"])
def health():
    """Kiểm tra backend + DB + PostGIS đã sống chưa."""
    with pool.connection() as conn:
        row = conn.execute("SELECT PostGIS_Version() AS postgis").fetchone()
    return {"status": "ok", "postgis": row["postgis"]}
