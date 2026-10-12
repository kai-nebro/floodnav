"""Các tham số của hệ thống tìm đường. Chỉnh ở đây để thử nghiệm."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = ROOT / "data" / "hanoi_drive.graphml"

METRIC_CRS = 32648          # UTM 48N: hệ toạ độ mét cho Hà Nội

# --- Mực nước -> trọng số ---
FLOOD_RADIUS_M = 60         # điểm ngập ảnh hưởng tới các đoạn đường trong bán kính này
PENALTY_START_CM = 5        # dưới 5 cm coi như không ngập
PENALTY_ALPHA = 8.0         # càng sát ngưỡng chặn, đoạn đường càng "đắt" (tối đa 1 + 8 = 9 lần)
CAR_LIMIT_FACTOR = 1.5      # ngưỡng ô tô = ngưỡng điểm ngập x 1.5 (xe máy 20 cm -> ô tô 30 cm)

# Mức người dân báo -> độ sâu ước lượng (cm)
LEVEL_DEPTH_CM = {"light": 10, "medium": 25, "heavy": 40}

# Tốc độ trung bình ước tính trong phố (km/h), chỉ dùng để ước lượng thời gian
SPEED_KMH = {"motorbike": 25, "car": 30}

MAX_SNAP_M = 500            # điểm xuất phát/đích cách đường gần nhất quá 500 m thì báo lỗi
