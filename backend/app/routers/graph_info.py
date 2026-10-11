"""Thông tin đồ thị đường đã nạp (để kiểm tra nhanh)."""
from fastapi import APIRouter, HTTPException

from ..graph import GRAPH_PATH, GraphNotReady, get_graph

router = APIRouter(prefix="/api/graph", tags=["Bản đồ đường"])


@router.get("/info")
def graph_info():
    try:
        G = get_graph()
    except GraphNotReady as e:
        raise HTTPException(503, str(e))

    xs = [d["x"] for _, d in G.nodes(data=True)]
    ys = [d["y"] for _, d in G.nodes(data=True)]

    streets = set()
    for _, _, d in G.edges(data=True):
        name = d.get("name")
        if isinstance(name, list):
            name = name[0] if name else None
        if name:
            streets.add(name)

    return {
        "nodes": len(G.nodes),          # số nút giao
        "edges": len(G.edges),          # số đoạn đường
        "named_streets": len(streets),
        "sample_streets": sorted(streets)[:8],
        "bbox": {"west": min(xs), "south": min(ys), "east": max(xs), "north": max(ys)},
        "file_mb": round(GRAPH_PATH.stat().st_size / 1_000_000, 1),
    }
