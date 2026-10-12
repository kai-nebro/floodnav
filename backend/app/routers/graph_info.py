"""Thông tin đồ thị đường và các đoạn đường đang bị ảnh hưởng bởi ngập."""
from fastapi import APIRouter, HTTPException

from .. import config
from ..graph import GraphNotReady, fetch_flood_sources, get_graph

router = APIRouter(prefix="/api/graph", tags=["Bản đồ đường"])


def _graph_or_503():
    try:
        return get_graph()
    except GraphNotReady as e:
        raise HTTPException(503, str(e))


def _edge_coords(G, u, v, data) -> list:
    """Danh sách [lng, lat] của một đoạn đường, theo chiều u -> v."""
    ux, uy = G.nodes[u]["x"], G.nodes[u]["y"]
    geom = data.get("geometry")
    if geom is None:
        return [[ux, uy], [G.nodes[v]["x"], G.nodes[v]["y"]]]
    pts = [[x, y] for x, y in geom.coords]
    d_first = (pts[0][0] - ux) ** 2 + (pts[0][1] - uy) ** 2
    d_last = (pts[-1][0] - ux) ** 2 + (pts[-1][1] - uy) ** 2
    return pts[::-1] if d_first > d_last else pts


@router.get("/info")
def graph_info():
    rg = _graph_or_503()
    G = rg.G

    streets = set()
    for _, _, d in G.edges(data=True):
        name = d.get("name")
        if isinstance(name, list):
            name = name[0] if name else None
        if name:
            streets.add(name)

    return {
        "nodes": len(G.nodes),
        "edges": len(G.edges),
        "named_streets": len(streets),
        "sample_streets": sorted(streets)[:8],
        "bbox": {"west": float(rg.node_lng.min()), "south": float(rg.node_lat.min()),
                 "east": float(rg.node_lng.max()), "north": float(rg.node_lat.max())},
        "file_mb": round(config.GRAPH_PATH.stat().st_size / 1_000_000, 1),
    }


@router.get("/flood-edges")
def flood_edges(vehicle: str = "motorbike"):
    """
    Các đoạn đường đang bị ảnh hưởng bởi ngập (GeoJSON), kèm cờ 'blocked' theo loại xe.
    vehicle = motorbike | car. Xem phần 'summary' ở đầu kết quả để kiểm tra nhanh.
    """
    if vehicle not in ("motorbike", "car"):
        raise HTTPException(422, "vehicle phải là 'motorbike' hoặc 'car'")

    rg = _graph_or_503()
    sources = fetch_flood_sources()
    flood = rg.flood_edges(sources)
    factor = config.CAR_LIMIT_FACTOR if vehicle == "car" else 1.0

    features, by_source, blocked_count = [], {}, 0
    for (u, v, k), f in flood.items():
        limit = f["threshold_cm"] * factor
        blocked = f["depth_cm"] >= limit
        blocked_count += blocked
        by_source[f["name"]] = by_source.get(f["name"], 0) + 1
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": _edge_coords(rg.G, u, v, rg.G[u][v][k])},
            "properties": {"source": f["name"], "depth_cm": f["depth_cm"],
                           "limit_cm": round(limit, 1), "blocked": blocked},
        })

    matched = {(f["kind"], f["source_id"]) for f in flood.values()}
    unmatched = [s["name"] for s in sources
                 if s["depth_cm"] >= config.PENALTY_START_CM and (s["kind"], s["source_id"]) not in matched]

    return {
        "summary": {
            "vehicle": vehicle,
            "affected_segments": len(features),
            "blocked_segments": blocked_count,
            "segments_per_source": by_source,
            "sources_without_road": unmatched,   # điểm ngập không khớp được với đoạn đường nào
        },
        "type": "FeatureCollection",
        "features": features,
    }
