# FloodNav – Bản đồ thông minh cảnh báo & điều hướng tránh ngập (Hà Nội)

## Yêu cầu
- Python 3.10+ (khi cài nhớ tick "Add Python to PATH")
- PostgreSQL 16 + PostGIS (không cần Docker)

## Cài đặt (Windows)
1. Cài PostgreSQL từ https://www.postgresql.org/download/windows/ (nhớ mật khẩu user `postgres`, giữ port 5432).
2. Cuối bước cài, chọn mở **Stack Builder** -> chọn PostgreSQL của bạn -> *Spatial Extensions* -> tick **PostGIS** -> cài.
3. Mở terminal tại thư mục `floodnav`:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
copy .env.example .env      # rồi mở .env, sửa MATKHAU
python db/setup_db.py
```

## Chạy backend
```bash
cd backend
uvicorn app.main:app --reload
```
- Health:      http://localhost:8000/api/health
- Điểm ngập:   http://localhost:8000/api/flood-points
- Swagger UI:  http://localhost:8000/docs

## Reset database (khi sửa file .sql)
```bash
python db/setup_db.py --reset
```

## Mac / Linux
- Mac: `brew install postgresql@16 postgis`, rồi `brew services start postgresql@16`
- Ubuntu: `sudo apt install postgresql postgis`
- Kích hoạt venv bằng `source venv/bin/activate`, copy file env bằng `cp .env.example .env`
