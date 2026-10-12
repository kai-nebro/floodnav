"""Nạp đồ thị OSM một lần, ghép điểm ngập (từ DB) vào các đoạn đường gần đó."""
import logging
import math
import threading

import geopandas as gpd
import numpy as np
import osmnx as ox

from . import config
from .db import pool

log = logging.getLogger("floodnav.graph")
_lock = threading.Lock()
_graph = None


class GraphNotReady(Exception):
    pass


class RoadGraph:
    def __init__(self, G):
        self.G = G
        ids = list(G.nodes)
        self.node_ids = np.array(ids)
        self.node_lng = np.array([G.nodes[n]["x"] for n in ids])
        self.node_lat = np.array([G.nodes[n]["y"] for n in ids])

        edges = ox.graph_to_gdfs(G, nodes=False)
        self.edge_keys = [(int(u), int(v), int(k)) for u, v, k in edges.index]
        self.edges_m = edges.to_crs(config.METRIC_CRS)
        self.edges_m.sindex      # dựng chỉ mục không gian trước

    def nearest_node(self, lng: float, lat: float):
        """Nút giao gần nhất và khoảng cách (m)."""
        k = math.cos(math.radians(lat))
        d2 = ((self.node_lng - lng) * k) ** 2 + (self.node_lat - lat) ** 2
        i = int(d2.argmin())
        return int(self.node_ids[i]), math.sqrt(float(d2[i])) * 111_320

    def flood_edges(self, sources: list) -> dict:
        """
        sources: [{lng, lat, depth_cm, threshold_cm, name, kind, source_id}, ...]
        Trả về {(u, v, key): thông tin ngập} cho các đoạn đường nằm trong bán kính ảnh hưởng.
        Đoạn đường chịu nhiều nguồn thì lấy nguồn ngập sâu nhất.
        """
        usable = [s for s in sources if s["depth_cm"] >= config.PENALTY_START_CM]
        result = {}
        if not usable:
            return result

        pts = gpd.GeoSeries(
            gpd.points_from_xy([s["lng"] for s in usable], [s["lat"] for s in usable]),
            crs=4326,
        ).to_crs(config.METRIC_CRS)

        for s, pt in zip(usable, pts):
            hits = self.edges_m.sindex.query(pt.buffer(config.FLOOD_RADIUS_M), predicate="intersects")
            for i in hits:
                key = self.edge_keys[int(i)]
                cur = result.get(key)
                if cur is None or s["depth_cm"] > cur["depth_cm"]:
                    result[key] = {
                        "depth_cm": s["depth_cm"], "threshold_cm": s["threshold_cm"],
                        "name": s["name"], "kind": s["kind"], "source_id": s["source_id"],
                    }
        return result


def get_graph() -> RoadGraph:
    """Nạp đồ thị ở lần gọi đầu tiên (mất vài giây), các lần sau dùng lại bản trong RAM."""
    global _graph
    if _graph is None:
        with _lock:
            if _graph is None:
                if not config.GRAPH_PATH.exists():
                    raise GraphNotReady(
                        "Chưa có dữ liệu bản đồ. Hãy chạy: python scripts/download_graph.py")
                log.info("Đang nạp đồ thị đường từ %s ...", config.GRAPH_PATH)
                _graph = RoadGraph(ox.load_graphml(config.GRAPH_PATH))
                log.info("Nạp xong: %d nút, %d đoạn", len(_graph.G.nodes), len(_graph.G.edges))
    return _graph


# ---------------------------------------------------------------- nguồn ngập từ DB
POINTS_SQL = """
    SELECT fp.id, fp.name, fp.threshold_cm, ST_X(fp.geom) AS lng, ST_Y(fp.geom) AS lat, r.depth_cm
    FROM flood_points fp
    JOIN LATERAL (
        SELECT depth_cm FROM water_readings
        WHERE point_id = fp.id ORDER BY recorded_at DESC LIMIT 1
    ) r ON TRUE
"""

REPORTS_SQL = """
    SELECT id, level, ST_X(geom) AS lng, ST_Y(geom) AS lat
    FROM reports WHERE confirmed AND expires_at > now()
"""


def fetch_flood_sources() -> list:
    """Mực nước hiện tại: số đo mới nhất của mỗi điểm ngập + báo cáo đã xác nhận còn hiệu lực."""
    with pool.connection() as conn:
        points = conn.execute(POINTS_SQL).fetchall()
        reports = conn.execute(REPORTS_SQL).fetchall()

    sources = [
        {"lng": p["lng"], "lat": p["lat"], "depth_cm": float(p["depth_cm"]),
         "threshold_cm": p["threshold_cm"], "name": p["name"], "kind": "point", "source_id": p["id"]}
        for p in points
    ]
    sources += [
        {"lng": r["lng"], "lat": r["lat"], "depth_cm": float(config.LEVEL_DEPTH_CM[r["level"]]),
         "threshold_cm": 20, "name": "Báo cáo của người dân", "kind": "report", "source_id": r["id"]}
        for r in reports
    ]
    return sources
