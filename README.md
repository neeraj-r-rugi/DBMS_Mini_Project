# Used Car Appraisal and Management System

This repository contains a Next.js frontend, FastAPI backend, KNN appraisal
pipeline, and MySQL/CouchDB database scripts.

## Project structure

```text
backend/                 FastAPI API and local SQLite demo adapter
database/                MySQL DDL and CouchDB setup script
scripts/train_model.py   Reproducible model training entry point
frontend/                Next.js App Router application
used_cars_dataset_v2.csv Training data
used_cars_knn_model.pkl  Trained model artifact
```

## 1. Train the model

The checked-in artifact can be used immediately. To regenerate it:

```bash
python -m pip install -r backend/requirements.txt
python scripts/train_model.py
```

The script cleans formatted rupee/mileage values, normalizes categorical
features, trains the KNN pipeline, prints MAE/RMSE/R², and writes
`used_cars_knn_model.pkl`.

## 2. Start the backend

For a zero-configuration local demo, the API uses `backend/demo.db` (SQLite)
and seeds the brand/model catalog from the CSV:

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Set `DATABASE_URL`, `COUCHDB_URL`, and `MODEL_PATH` in `backend/.env` when using
MySQL, CouchDB, or a model at a different path. Apply the MySQL schema with a
MySQL client:

```bash
mysql -u root -p < database/mysql_schema.sql
```

If the distribution's MySQL `root` account uses socket authentication, create
the application user first from an administrator shell:

```bash
sudo mysql < database/create_app_user.sql
```

Then set the matching URL in `backend/.env`:

```env
DATABASE_URL=mysql+pymysql://used_car_app:314159@127.0.0.1:3306/used_car_db
```

For CouchDB, install and start CouchDB using your operating system's package
manager or the Apache CouchDB distribution. Then initialize the databases and
Mango indexes:

```bash
sudo systemctl enable --now couchdb
COUCHDB_URL=http://127.0.0.1:5984 \
COUCHDB_USER=admin COUCHDB_PASSWORD=your-password \
./database/couchdb_schema.sh
```

MySQL provides the required `CAR`, `OWNER`, `APPRAISAL`, `SERVICE_HISTORY`,
`INSURANCE`, and `REGISTRATION` tables, indexes, `vw_car_inventory`,
`sp_get_cars_by_budget`, `fn_car_age`, and validation/default triggers. On
startup, the backend also creates its API catalog tables (`brands`,
`car_models`, and `inventory`) and mirrors inventory rows into `CAR` and
`APPRAISAL`, so both the API and coursework queries show the same cars.
CouchDB provides the `used_car` and `used_car_service_history` databases.
Documents retain the `Car` and `ServiceHistory` shapes and are linked by
`car_id` and `service_id`. CouchDB is optional; when it is unavailable,
metadata is omitted from details responses while service records continue to
be stored in MySQL `SERVICE_HISTORY`.

Useful API calls:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/brands
curl -X POST http://localhost:8000/api/appraisals \
  -H 'Content-Type: application/json' \
  -d '{"brand":"honda","model":"city","year":2020,"km_driven":40000,"transmission":"manual","owner":"first","fuel_type":"petrol"}'
curl 'http://localhost:8000/api/inventory?status=available'
```

## 3. Start the frontend

From the `frontend/` directory (there are two app directories in this legacy
workspace; use this canonical one):

```bash
cd frontend
npm install
cp .env.example .env.local
# .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

If you start the root-level Next.js app instead, its
`.env.local` must contain `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`. The
canonical `frontend/.env.local` already contains this setting.

Open `http://localhost:3000/appraise`, `/inventory`, or `/catalog`.
`/appraise` calls the ML endpoint, `/inventory` displays managed stock, and
`/catalog` provides a public searchable and budget-filtered listing. When the
API URL is omitted, the UI uses a small preview dataset.

The public inventory cards are clickable. They open the vehicle's relational
details plus its CouchDB condition, features, accident history, and service
records. To manage cars, open the unlinked private URL
`http://localhost:3000/admin/inventory`; enter the `ADMIN_PASSWORD` from
`backend/.env`. The private page can add cars (including CouchDB metadata) and
remove cars. It also supports an optional first service record while adding a
car and adding service records to existing cars. The backend protects these
operations with HTTP Basic authentication at `/api/admin/inventory`.

Cars created before CouchDB metadata persistence was fixed will not have
condition or accident documents automatically; add their metadata/service
records from the private admin page, or create them again after CouchDB is
available.

## Verification

1. Open `/appraise`, submit the default Honda City example, and verify a rupee
   estimate is returned.
2. Open `/inventory` and verify the seeded API catalog responds.
3. Add a car with `POST /api/inventory`, then refresh `/inventory` and filter
   by its brand or fuel type.
4. Open `/catalog`, search by model, and enter a maximum budget.
5. For a database deployment, insert a `CAR` row and verify the
   `trg_car_default_appraisal` trigger creates an `APPRAISAL` row; run
   `CALL sp_get_cars_by_budget(1000000)`.
