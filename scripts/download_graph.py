"""
Tải đồ thị đường (xe cộ) khu vực nội thành phía Tây Hà Nội từ OpenStreetMap
và lưu vào data/hanoi_drive.graphml.

Chạy:  python scripts/download_graph.py
Cần Internet, mất khoảng 1-5 phút. Chỉ cần chạy 1 lần.
Script tự thử lần lượt nhiều máy chủ Overpass nếu máy chủ đầu bị lỗi/chậm.
"""
import sys
from pathlib import Path

import osmnx as ox

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hanoi_drive.graphml"

# (tây, nam, đông, bắc) -> phủ Cầu Giấy, Đống Đa, Thanh Xuân, Nam Từ Liêm; bao đủ 8 điểm ngập mẫu
BBOX = (105.772, 21.003, 105.831, 21.052)

# Các máy chủ Overpass (thử lần lượt)
ENDPOINTS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
]

ox.settings.requests_timeout = 300


def main():
    OUT.parent.mkdir(exist_ok=True)
    G = None

    for url in ENDPOINTS:
        print(f"Đang tải đường từ {url} (khung {BBOX}) ...")
        ox.settings.overpass_url = url
        try:
            G = ox.graph_from_bbox(BBOX, network_type="drive")
            break
        except Exception as e:
            print(f"  -> Lỗi: {type(e).__name__}. Thử máy chủ khác...\n")

    if G is None:
        sys.exit(
            "Không tải được từ máy chủ nào.\n"
            "-> Thử: tắt VPN/proxy, đổi sang mạng khác (ví dụ phát 4G từ điện thoại), "
            "hoặc chạy lại sau vài phút."
        )

    # Giữ thành phần liên thông mạnh lớn nhất để chắc chắn tìm được đường đi 2 chiều
    G = ox.truncate.largest_component(G, strongly=True)

    ox.save_graphml(G, OUT)
    size_mb = OUT.stat().st_size / 1_000_000
    print(f"Xong! {len(G.nodes):,} nút giao, {len(G.edges):,} đoạn đường -> {OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
