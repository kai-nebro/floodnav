"""Nạp đồ thị đường OSM một lần, dùng lại cho mọi request."""
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = ROOT / "data" / "hanoi_drive.graphml"

_lock = threading.Lock()
_graph = None


class GraphNotReady(Exception):
    pass


def get_graph():
    """Nạp đồ thị ở lần gọi đầu tiên (mất vài giây), các lần sau dùng lại bản trong RAM."""
    global _graph
    if _graph is None:
        with _lock:
            if _graph is None:
                if not GRAPH_PATH.exists():
                    raise GraphNotReady(
                        "Chưa có dữ liệu bản đồ. Hãy chạy: python scripts/download_graph.py")
                import osmnx as ox   # import ở đây để backend khởi động nhanh

                print("[FloodNav] Đang nạp bản đồ đường vào bộ nhớ ...", flush=True)
                t0 = time.time()
                _graph = ox.load_graphml(GRAPH_PATH)
                print(f"[FloodNav] Nạp xong sau {time.time() - t0:.1f} giây.", flush=True)
    return _graph
