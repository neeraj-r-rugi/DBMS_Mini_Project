"""Database adapters for SQLite demo mode and MySQL deployment mode."""

from contextlib import contextmanager
import csv
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

from .config import DB_URL, ROOT

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS car_models (id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(brand_id,name), FOREIGN KEY(brand_id) REFERENCES brands(id));
CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, model_id INTEGER NOT NULL, year INTEGER NOT NULL, km_driven REAL NOT NULL DEFAULT 0, transmission TEXT NOT NULL, owner TEXT NOT NULL, fuel_type TEXT NOT NULL, asking_price REAL NOT NULL, status TEXT NOT NULL DEFAULT 'available', registration_no TEXT UNIQUE, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(brand_id) REFERENCES brands(id), FOREIGN KEY(model_id) REFERENCES car_models(id));
CREATE TABLE IF NOT EXISTS appraisals (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, brand_id INTEGER NOT NULL, model_id INTEGER NOT NULL, year INTEGER NOT NULL, km_driven REAL NOT NULL, transmission TEXT NOT NULL, owner TEXT NOT NULL, fuel_type TEXT NOT NULL, estimated_price REAL NOT NULL, model_version TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_models_brand ON car_models(brand_id);
CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(brand_id,model_id,status);
CREATE INDEX IF NOT EXISTS idx_inventory_price ON inventory(asking_price);
CREATE VIEW IF NOT EXISTS available_inventory AS SELECT i.id,b.name brand,m.name model,i.year,i.km_driven,i.transmission,i.owner,i.fuel_type,i.asking_price,i.description,i.registration_no FROM inventory i JOIN brands b ON b.id=i.brand_id JOIN car_models m ON m.id=i.model_id WHERE i.status='available';
"""


def _sqlite_path() -> str:
    value = DB_URL.removeprefix("sqlite:///")
    return ":memory:" if value == ":memory:" else str(ROOT / value) if not value.startswith("/") else value


@contextmanager
def connection():
    if DB_URL.startswith(("mysql://", "mysql+pymysql://")):
        try:
            import pymysql
            url = urlparse(DB_URL.replace("mysql+pymysql://", "mysql://"))
            conn = pymysql.connect(
                host=url.hostname or "localhost",
                port=url.port or 3306,
                user=url.username or "root",
                password=url.password or "",
                database=url.path.lstrip("/") or "used_car_db",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
        except Exception as exc:
            raise RuntimeError("MySQL connection failed; check DATABASE_URL and credentials") from exc
        try:
            yield conn
        finally:
            conn.close()
        return

    path = _sqlite_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        if DB_URL.startswith(("mysql://", "mysql+pymysql://")):
            with conn.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS brands (id BIGINT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS car_models (id BIGINT AUTO_INCREMENT PRIMARY KEY, brand_id BIGINT NOT NULL, name VARCHAR(120) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_brand_model (brand_id, name), FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE)"
                )
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS inventory (id BIGINT AUTO_INCREMENT PRIMARY KEY, brand_id BIGINT NOT NULL, model_id BIGINT NOT NULL, year SMALLINT NOT NULL, km_driven DECIMAL(12,2) NOT NULL DEFAULT 0, transmission VARCHAR(30) NOT NULL, owner VARCHAR(30) NOT NULL, fuel_type VARCHAR(30) NOT NULL, asking_price DECIMAL(14,2) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'available', registration_no VARCHAR(40) UNIQUE, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, FOREIGN KEY (brand_id) REFERENCES brands(id), FOREIGN KEY (model_id) REFERENCES car_models(id))"
                )
            _seed_mysql_catalog(conn)
            return

        conn.executescript(SQLITE_SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0] == 0:
            dataset = ROOT / "used_cars_dataset_v2.csv"
            if dataset.exists():
                with dataset.open(newline="", encoding="utf-8") as stream:
                    pairs = {(row.get("Brand", "").strip(), row.get("model", "").strip()) for row in csv.DictReader(stream)}
                for brand, model in sorted(pairs):
                    if brand and model:
                        conn.execute("INSERT OR IGNORE INTO brands(name) VALUES (?)", (brand,))
                        brand_id = conn.execute("SELECT id FROM brands WHERE name=?", (brand,)).fetchone()[0]
                        conn.execute("INSERT OR IGNORE INTO car_models(brand_id,name) VALUES (?,?)", (brand_id, model))


def _number(value: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _seed_mysql_catalog(conn) -> None:
    """Seed reference data and 100 available cars for a fresh MySQL install."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM brands")
        brands_exist = cursor.fetchone()["count"] > 0
        dataset = ROOT / "used_cars_dataset_v2.csv"
        if not dataset.exists():
            return
        with dataset.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if not brands_exist:
            for row in rows:
                brand = row.get("Brand", "").strip()
                model = row.get("model", "").strip()
                if brand and model:
                    cursor.execute("INSERT IGNORE INTO brands(name) VALUES (%s)", (brand,))
                    cursor.execute("SELECT id FROM brands WHERE LOWER(name)=LOWER(%s)", (brand,))
                    brand_id = cursor.fetchone()["id"]
                    cursor.execute(
                        "INSERT IGNORE INTO car_models(brand_id,name) VALUES (%s,%s)",
                        (brand_id, model),
                    )

        cursor.execute("SELECT COUNT(*) AS count FROM inventory")
        if cursor.fetchone()["count"]:
            return
        inserted = 0
        for row in rows:
            year = _number(row.get("Year", ""))
            mileage = _number(row.get("kmDriven", ""))
            price = _number(row.get("AskPrice", ""))
            brand = row.get("Brand", "").strip()
            model = row.get("model", "").strip()
            if not brand or not model or not year or mileage is None or not price or price <= 0:
                continue
            cursor.execute(
                "SELECT b.id AS brand_id, m.id AS model_id FROM brands b "
                "JOIN car_models m ON m.brand_id=b.id WHERE LOWER(b.name)=LOWER(%s) "
                "AND LOWER(m.name)=LOWER(%s) LIMIT 1",
                (brand, model),
            )
            ids = cursor.fetchone()
            if not ids:
                continue
            cursor.execute(
                "INSERT INTO inventory (brand_id,model_id,year,km_driven,transmission,owner,"
                "fuel_type,asking_price,status,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'available',%s)",
                (
                    ids["brand_id"],
                    ids["model_id"],
                    int(year),
                    mileage,
                    row.get("Transmission", "Manual").strip() or "Manual",
                    row.get("Owner", "First").strip() or "First",
                    row.get("FuelType", "Petrol").strip() or "Petrol",
                    price,
                    row.get("AdditionInfo", "").strip() or None,
                ),
            )
            inserted += 1
            if inserted >= 100:
                break


def query(sql: str, params=(), fetch: bool = False):
    with connection() as conn:
        is_mysql = DB_URL.startswith(("mysql://", "mysql+pymysql://"))
        statement = sql.replace("?", "%s") if is_mysql else sql
        if is_mysql:
            statement = statement.replace("INSERT OR IGNORE", "INSERT IGNORE")
        cursor = conn.cursor()
        try:
            cursor.execute(statement, params)
            if fetch:
                return list(cursor.fetchall())
            return cursor.lastrowid if hasattr(cursor, "lastrowid") else cursor.rowcount
        finally:
            cursor.close()
