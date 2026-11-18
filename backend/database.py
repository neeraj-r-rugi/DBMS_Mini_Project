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
                _ensure_mysql_coursework_schema(cursor)
            _seed_mysql_catalog(conn)
            _sync_mysql_cars(conn)
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


def _ensure_mysql_coursework_schema(cursor) -> None:
    """Create the coursework tables used by MySQL deployments."""
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS CAR (car_id VARCHAR(50) PRIMARY KEY, "
        "brand VARCHAR(50) NOT NULL, model VARCHAR(100) NOT NULL, year SMALLINT NOT NULL, "
        "fuel_type VARCHAR(30) NOT NULL, transmission VARCHAR(30) NOT NULL, "
        "km_driven INT UNSIGNED NOT NULL, purchase_price DECIMAL(12,2) NOT NULL, "
        "status ENUM('available','reserved','sold','archived') NOT NULL DEFAULT 'available', "
        "created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS OWNER (owner_id VARCHAR(50) PRIMARY KEY, "
        "name VARCHAR(100) NOT NULL, contact VARCHAR(50) NOT NULL, car_id VARCHAR(50) NOT NULL, "
        "FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS APPRAISAL (appraisal_id VARCHAR(50) PRIMARY KEY, "
        "car_id VARCHAR(50) NOT NULL, appraisal_date DATE NOT NULL, "
        "predicted_price DECIMAL(12,2) NOT NULL, final_price DECIMAL(12,2), "
        "model_version VARCHAR(80), FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS SERVICE_HISTORY (service_id VARCHAR(50) PRIMARY KEY, "
        "car_id VARCHAR(50) NOT NULL, service_date DATE NOT NULL, "
        "service_cost DECIMAL(10,2) NOT NULL, service_details TEXT NOT NULL, "
        "FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE)"
    )
    cursor.execute(
        "SELECT COUNT(*) AS count FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='SERVICE_HISTORY' "
        "AND COLUMN_NAME='service_details'"
    )
    if cursor.fetchone()["count"] == 0:
        cursor.execute(
            "ALTER TABLE SERVICE_HISTORY ADD COLUMN service_details TEXT NULL"
        )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS INSURANCE (insurance_id VARCHAR(50) PRIMARY KEY, "
        "car_id VARCHAR(50) NOT NULL, policy_number VARCHAR(100) NOT NULL UNIQUE, "
        "insurer VARCHAR(100) NOT NULL, policy_type VARCHAR(50) NOT NULL, "
        "start_date DATE NOT NULL, expiry_date DATE NOT NULL, "
        "FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS REGISTRATION (registration_id VARCHAR(50) PRIMARY KEY, "
        "car_id VARCHAR(50) NOT NULL UNIQUE, registration_number VARCHAR(50) NOT NULL UNIQUE, "
        "registration_date DATE NOT NULL, rto_code VARCHAR(20) NOT NULL, "
        "registration_state VARCHAR(50) NOT NULL, registration_type VARCHAR(50) NOT NULL, "
        "FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE)"
    )


def _sync_mysql_cars(conn) -> None:
    """Mirror API inventory rows into the coursework CAR and APPRAISAL tables."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT i.id, b.name AS brand, m.name AS model, i.year, i.fuel_type, "
            "i.transmission, i.km_driven, i.asking_price, i.status "
            "FROM inventory i JOIN brands b ON b.id=i.brand_id "
            "JOIN car_models m ON m.id=i.model_id"
        )
        for row in cursor.fetchall():
            car_id = f"CAR_{row['id']}"
            cursor.execute(
                "INSERT INTO CAR (car_id, brand, model, year, fuel_type, transmission, "
                "km_driven, purchase_price, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE brand=VALUES(brand), model=VALUES(model), "
                "year=VALUES(year), fuel_type=VALUES(fuel_type), transmission=VALUES(transmission), "
                "km_driven=VALUES(km_driven), purchase_price=VALUES(purchase_price), status=VALUES(status)",
                (car_id, row["brand"], row["model"], row["year"], row["fuel_type"],
                 row["transmission"], row["km_driven"], row["asking_price"], row["status"]),
            )
            cursor.execute(
                "INSERT IGNORE INTO APPRAISAL "
                "(appraisal_id, car_id, appraisal_date, predicted_price, final_price, model_version) "
                "VALUES (%s,%s,CURRENT_DATE,%s,%s,'inventory-initial')",
                (f"AUTO_{car_id}", car_id, row["asking_price"], row["asking_price"]),
            )


def sync_mysql_car(car_id: int) -> None:
    if DB_URL.startswith(("mysql://", "mysql+pymysql://")):
        with connection() as conn:
            _sync_mysql_cars(conn)


def add_mysql_service(car_id: int, service_id: str, service_date: str, service_cost: float, details: str) -> None:
    if DB_URL.startswith(("mysql://", "mysql+pymysql://")):
        query(
            "INSERT INTO SERVICE_HISTORY (service_id, car_id, service_date, service_cost, service_details) "
            "VALUES (?,?,?,?,?)",
            (service_id, f"CAR_{car_id}", service_date, service_cost, details),
        )


def get_mysql_services(car_id: int) -> list:
    if not DB_URL.startswith(("mysql://", "mysql+pymysql://")):
        return []
    return query(
        "SELECT service_id, car_id, service_date, service_cost, service_details "
        "FROM SERVICE_HISTORY WHERE car_id=? ORDER BY service_date DESC, service_id DESC",
        (f"CAR_{car_id}",),
        True,
    )


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
