"""
Tạo database + nạp schema + dữ liệu mẫu, không cần dùng psql.

Chạy:   python db/setup_db.py            (tạo mới, bỏ qua nếu đã có dữ liệu)
        python db/setup_db.py --reset    (XOÁ database rồi tạo lại từ đầu)
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

if "DATABASE_URL" not in os.environ:
    sys.exit("Thiếu DATABASE_URL. Hãy tạo file .env (copy từ .env.example) và điền mật khẩu.")

info = conninfo_to_dict(os.environ["DATABASE_URL"])
dbname = info.get("dbname", "floodnav")
admin_conninfo = make_conninfo(**{**info, "dbname": "postgres"})
app_conninfo = make_conninfo(**info)

reset = "--reset" in sys.argv

try:
    admin = psycopg.connect(admin_conninfo, autocommit=True)
except psycopg.OperationalError as e:
    sys.exit(f"Không kết nối được PostgreSQL: {e}\n"
             "-> Kiểm tra PostgreSQL đã chạy chưa, và mật khẩu trong .env có đúng không.")

with admin:
    if reset:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()", (dbname,))
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(dbname)))
        print(f"Đã xoá database '{dbname}'.")

    exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
    if not exists:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        print(f"Đã tạo database '{dbname}'.")

with psycopg.connect(app_conninfo) as conn:
    already = conn.execute("SELECT to_regclass('public.flood_points')").fetchone()[0]
    if already:
        print("Schema đã tồn tại, bỏ qua. (Dùng --reset nếu muốn tạo lại từ đầu.)")
        sys.exit(0)

    try:
        for f in sorted((ROOT / "db" / "init").glob("*.sql")):
            print(f"Chạy {f.name} ...")
            conn.execute(f.read_text(encoding="utf-8"))
        conn.commit()
    except psycopg.errors.FeatureNotSupported as e:
        sys.exit(f"Lỗi PostGIS: {e}\n-> Có vẻ chưa cài PostGIS. Xem README, bước cài PostGIS bằng Stack Builder.")
    except psycopg.errors.UndefinedFile as e:
        sys.exit(f"Lỗi PostGIS: {e}\n-> Có vẻ chưa cài PostGIS. Xem README, bước cài PostGIS bằng Stack Builder.")

print("Xong! Database đã sẵn sàng.")
