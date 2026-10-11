"""
Tải đồ thị đường (xe cộ) khu vực nội thành phía Tây Hà Nội từ OpenStreetMap
và lưu vào data/hanoi_drive.graphml.

Chạy:  python scripts/download_graph.py
Cần Internet, mất khoảng 1-5 phút. Chỉ cần chạy 1 lần.
"""
from pathlib import Path

import osmnx as ox

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hanoi_drive.graphml"

# (tây, nam, đông, bắc) -> phủ Cầu Giấy, Đống Đa, Thanh Xuân, Nam Từ Liêm, Tây Hồ
BBOX = (105.765, 20.995, 105.840, 21.060)


def main():
    OUT.parent.mkdir(exist_ok=True)
    print(f"Đang tải đường từ OpenStreetMap, khung {BBOX} ...")
    G = ox.graph_from_bbox(BBOX, network_type="drive")

    # Giữ thành phần liên thông mạnh lớn nhất để chắc chắn tìm được đường đi 2 chiều
    G = ox.truncate.largest_component(G, strongly=True)

    ox.save_graphml(G, OUT)
    size_mb = OUT.stat().st_size / 1_000_000
    print(f"Xong! {len(G.nodes):,} nút giao, {len(G.edges):,} đoạn đường -> {OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
