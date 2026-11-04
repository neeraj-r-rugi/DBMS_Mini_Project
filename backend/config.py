from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL", "sqlite:///backend/demo.db")
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(ROOT / "used_cars_knn_model.pkl")))
COUCHDB_URL = os.getenv("COUCHDB_URL", "")
COUCHDB_USER = os.getenv("COUCHDB_USER", "")
COUCHDB_PASSWORD = os.getenv("COUCHDB_PASSWORD", "")
COUCHDB_CAR_DATABASE = os.getenv("COUCHDB_CAR_DATABASE", "used_car")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
