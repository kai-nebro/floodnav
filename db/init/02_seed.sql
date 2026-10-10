-- ============ Dữ liệu mẫu ============
-- LƯU Ý: toạ độ chỉ GẦN ĐÚNG. Hãy kiểm tra lại trên openstreetmap.org
-- (chuột phải vào bản đồ -> "Show address"/"Centre map here") rồi chỉnh cho khớp.

INSERT INTO users (name, vehicle) VALUES
  ('Demo Xe máy', 'motorbike'),
  ('Demo Ô tô',   'car');

-- ST_MakePoint(KINH ĐỘ, VĨ ĐỘ)  -> chú ý thứ tự lng, lat
INSERT INTO flood_points (name, geom, sensor_id, threshold_cm) VALUES
  ('Nguyễn Khánh Toàn',       ST_SetSRID(ST_MakePoint(105.7955, 21.0385), 4326), 'SENSOR-001', 20),
  ('Xuân Thủy - Cầu Giấy',    ST_SetSRID(ST_MakePoint(105.7820, 21.0370), 4326), 'SENSOR-002', 20),
  ('Trần Duy Hưng',           ST_SetSRID(ST_MakePoint(105.8010, 21.0105), 4326), 'SENSOR-003', 20),
  ('Phạm Hùng - Mễ Trì',      ST_SetSRID(ST_MakePoint(105.7770, 21.0280), 4326), 'SENSOR-004', 20),
  ('Chùa Bộc',                ST_SetSRID(ST_MakePoint(105.8260, 21.0085), 4326), 'SENSOR-005', 20),
  ('Nguyễn Chí Thanh',        ST_SetSRID(ST_MakePoint(105.8105, 21.0255), 4326), 'SENSOR-006', 20),
  ('Láng Hạ',                 ST_SetSRID(ST_MakePoint(105.8120, 21.0115), 4326), 'SENSOR-007', 20),
  ('Hoàng Quốc Việt',         ST_SetSRID(ST_MakePoint(105.7925, 21.0465), 4326), 'SENSOR-008', 20);

-- Vài số đo ban đầu để có dữ liệu hiển thị
INSERT INTO water_readings (point_id, depth_cm, source)
SELECT id, (ARRAY[0, 3, 12, 25, 8, 0, 18, 5])[id], 'sensor' FROM flood_points;
