"""
Tìm đường thông minh: A* với trọng số an toàn ngập nước.

cost(đoạn) = chiều dài × (1 + α · penalty)
    penalty = 0                       nếu độ sâu < 5 cm
            = (d - 5) / (ngưỡng - 5)  nếu 5 cm ≤ d < ngưỡng của xe
            = chặn (None)             nếu d ≥ ngưỡng của xe
"""
import math
from typing import Optional

import networkx as nx

from . import config


# ---------------------------------------------------------------- trọng số
def vehicle_limit(vehicle: str, threshold_cm: float) -> float:
    return threshold_cm * (config.CAR_LIMIT_FACTOR if vehicle == "car" else 1.0)


def flood_penalty(depth_cm: float, limit_cm: float) -> Optional[float]:
    """None = đường bị chặn. Ngược lại trả về hệ số phạt từ 0 đến <1."""
    if depth_cm >= limit_cm:
        return None
    if depth_cm < config.PENALTY_START_CM:
        return 0.0
    return (depth_cm - config.PENALTY_START_CM) / (limit_cm - config.PENALTY_START_CM)


def edge_cost(length: float, flood: Optional[dict], vehicle: str, mode: str) -> Optional[float]:
    """Chi phí 1 đoạn đường. None nghĩa là không đi được."""
    if mode == "fastest" or flood is None:
        return length
    pen = flood_penalty(flood["depth_cm"], vehicle_limit(vehicle, flood["threshold_cm"]))
    if pen is None:
        return None
    return length * (1 + config.PENALTY_ALPHA * pen)


def best_edge(G, flood_map: dict, u, v, vehicle: str, mode: str):
    """Trong các đoạn song song u->v, chọn đoạn rẻ nhất. Trả về (key, cost)."""
    best_k, best_c = None, None
    for k, data in G[u][v].items():
        c = edge_cost(data.get("length", 0.0), flood_map.get((u, v, k)), vehicle, mode)
        if c is not None and (best_c is None or c < best_c):
            best_k, best_c = k, c
    return best_k, best_c


# ---------------------------------------------------------------- A*
def _heuristic(G):
    def h(a, b):
        ya, xa = G.nodes[a]["y"], G.nodes[a]["x"]
        yb, xb = G.nodes[b]["y"], G.nodes[b]["x"]
        k = math.cos(math.radians((ya + yb) / 2))
        return math.hypot((xa - xb) * k, ya - yb) * 111_320   # mét, luôn <= chi phí thật
    return h


def find_path(G, flood_map: dict, origin, dest, vehicle: str, mode: str) -> list:
    """A* giữa 2 nút. Raise nx.NetworkXNoPath nếu mọi đường đều bị chặn."""
    def weight(u, v, key_dict):
        best = None
        for k, data in key_dict.items():
            c = edge_cost(data.get("length", 0.0), flood_map.get((u, v, k)), vehicle, mode)
            if c is not None and (best is None or c < best):
                best = c
        return best          # None = ẩn đoạn đường này khỏi đồ thị

    return nx.astar_path(G, origin, dest, heuristic=_heuristic(G), weight=weight)


# ---------------------------------------------------------------- mô tả lộ trình
def edge_coords(G, u, v, data) -> list:
    """Danh sách [lng, lat] của một đoạn đường, theo chiều u -> v."""
    ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
    geom = data.get("geometry")
    if geom is None:
        return [[ux, uy], [G.nodes[v]["x"], G.nodes[v]["y"]]]
    pts = [[x, y] for x, y in geom.coords]
    d_first = (pts[0][0] - ux) ** 2 + (pts[0][1] - uy) ** 2
    d_last = (pts[-1][0] - ux) ** 2 + (pts[-1][1] - uy) ** 2
    return pts[::-1] if d_first > d_last else pts


def _street_name(data) -> Optional[str]:
    name = data.get("name")
    if isinstance(name, list):
        name = name[0] if name else None
    return name


def describe_route(G, flood_map: dict, path: list, vehicle: str, mode: str) -> dict:
    coords, length, cost = [], 0.0, 0.0
    warnings = {}
    passable = True

    for u, v in zip(path[:-1], path[1:]):
        k, c = best_edge(G, flood_map, u, v, vehicle, mode)
        data = G[u][v][k]
        length += data.get("length", 0.0)
        cost += c
        seg = edge_coords(G, u, v, data)
        coords.extend(seg[1:] if coords and coords[-1] == seg[0] else seg)

        fl = flood_map.get((u, v, k))
        if fl:
            limit = vehicle_limit(vehicle, fl["threshold_cm"])
            blocked = fl["depth_cm"] >= limit
            passable = passable and not blocked
            wid = (fl["kind"], fl["source_id"])
            w = warnings.setdefault(wid, {
                "source": fl["name"], "kind": fl["kind"], "depth_cm": fl["depth_cm"],
                "limit_cm": round(limit, 1), "blocked": blocked, "street": _street_name(data),
            })
            w["street"] = w["street"] or _street_name(data)

    speed_m_per_min = config.SPEED_KMH[vehicle] * 1000 / 60
    return {
        "found": True,
        "mode": mode,
        "distance_m": round(length),
        "duration_min": round(length / speed_m_per_min, 1),
        "cost": round(cost),
        "passable": passable,       # false = lộ trình này vẫn đi xuyên đoạn bị chặn (chỉ xảy ra ở 'fastest')
        "flood_warnings": list(warnings.values()),
        "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]},
    }
