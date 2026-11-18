# Used Car Appraisal System: Database and Architecture Explanation

This document explains how the two database technologies in this project work
together:

1. **MySQL or SQLite** stores the structured, transactional part of the
   application: the car catalog, inventory, brand/model relationships, and
   appraisal inputs/results.
2. **CouchDB** stores flexible car metadata and service-history documents,
   which do not need a rigid relational schema.

The project also contains a KNN machine-learning model. The model is not a
database, but it participates in the appraisal flow by producing an estimated
price from vehicle attributes.

---

## 1. Overall architecture

```text
Next.js frontend
        |
        | HTTP/JSON
        v
FastAPI backend (backend/main.py)
        |
        +--> Relational adapter (backend/database.py)
        |       +--> SQLite backend/demo.db       [default local mode]
        |       +--> MySQL used_car_db             [deployment mode]
        |
        +--> CouchDB REST adapter (backend/couchdb.py)
        |       +--> used_car
        |       +--> used_car_service_history
        |
        +--> KNN model (used_cars_knn_model.pkl)
```

The frontend never connects directly to either database. It calls the FastAPI
API. This is important because the backend is responsible for validation,
authentication, joins, database selection, and combining data from both
database systems.

### Main responsibilities

| Component | Responsibility |
|---|---|
| Next.js frontend | Forms, catalog pages, inventory pages, and API calls |
| FastAPI | HTTP endpoints, Pydantic validation, admin authentication |
| SQLite/MySQL | Structured catalog and inventory records |
| CouchDB | Flexible car metadata and service records |
| KNN pipeline | Used-car price estimation |
| CSV files | Training data and initial brand/model/inventory seed data |

---

## 2. How the relational database is selected

The setting is read from `backend/config.py`:

```env
DATABASE_URL=sqlite:///backend/demo.db
```

This is the default, zero-configuration mode. The database file is
`backend/demo.db`.

For MySQL, the URL is changed to a MySQL URL, for example:

```env
DATABASE_URL=mysql+pymysql://used_car_app:password@127.0.0.1:3306/used_car_db
```

`backend/database.py` checks the prefix of `DATABASE_URL`:

- `sqlite:///...` opens a SQLite file.
- `mysql://...` or `mysql+pymysql://...` opens MySQL through PyMySQL.

The backend exposes a common `connection()` context manager and a common
`query()` helper. API code can therefore issue the same logical queries
without opening database connections itself. For MySQL, the adapter changes
the parameter placeholder from `?` to `%s` and translates
`INSERT OR IGNORE` to MySQL’s `INSERT IGNORE`.

When the FastAPI application starts, `startup()` calls `init_db()`:

- SQLite receives the local schema from the `SQLITE_SCHEMA` string.
- MySQL receives the runtime catalog/inventory tables if they do not already
  exist, and is seeded from `used_cars_dataset_v2.csv`.

---

## 3. Relational database design used by the backend

The runtime backend schema is deliberately smaller than the full academic
MySQL schema. It contains four SQLite tables and one view.

### 3.1 `brands`

`brands` is a reference table containing one row per vehicle brand.

| Column | Meaning |
|---|---|
| `id` | Auto-generated primary key |
| `name` | Brand name, such as Honda or Toyota |
| `created_at` | Time the brand row was created |

`name` is unique. This prevents duplicate brand records when an inventory item
is added. The API first inserts the brand if necessary and then looks it up to
obtain its numeric ID.

### 3.2 `car_models`

`car_models` contains models belonging to a brand.

| Column | Meaning |
|---|---|
| `id` | Auto-generated primary key |
| `brand_id` | Foreign key to `brands.id` |
| `name` | Model name, such as City or Corolla |
| `created_at` | Time the model row was created |

The pair `(brand_id, name)` is unique. This allows two different brands to
have models with the same name while preventing the same model from being
repeated under one brand.

Relationship:

```text
brands 1 ---- many car_models
```

### 3.3 `inventory`

`inventory` is the main structured table for cars currently managed by the
application.

| Column | Meaning |
|---|---|
| `id` | Internal numeric inventory ID |
| `brand_id` | Foreign key to `brands.id` |
| `model_id` | Foreign key to `car_models.id` |
| `year` | Manufacturing year |
| `km_driven` | Distance driven |
| `transmission` | Manual, automatic, etc. |
| `owner` | Ownership category, such as first owner |
| `fuel_type` | Petrol, diesel, electric, etc. |
| `asking_price` | Price requested for the inventory item |
| `status` | Usually `available`; may be reserved, sold, or another application status |
| `registration_no` | Optional unique registration number |
| `description` | Optional listing description |
| `created_at` | Creation timestamp |
| `updated_at` | Last-update timestamp |

The table stores `brand_id` and `model_id`, not repeated brand/model strings.
API responses join the table to `brands` and `car_models` to return readable
names.

Relationships:

```text
brands      1 ---- many inventory rows
car_models  1 ---- many inventory rows
```

Important indexes:

- `idx_inventory_lookup(brand_id, model_id, status)` helps catalog filtering.
- `idx_inventory_price(asking_price)` helps price-oriented queries.

### 3.4 `appraisals`

The SQLite schema also defines `appraisals`, which records price-estimation
requests/results.

| Column | Meaning |
|---|---|
| `id` | Auto-generated appraisal ID |
| `customer_id` | Optional customer reference |
| `brand_id`, `model_id` | Vehicle identity |
| `year`, `km_driven` | Numeric appraisal inputs |
| `transmission`, `owner`, `fuel_type` | Categorical appraisal inputs |
| `estimated_price` | Model-generated estimate |
| `model_version` | Version/name of the model used |
| `created_at` | Time of the appraisal |

The current `/api/appraisals` endpoint calculates and returns an estimate, but
does not currently insert a row into this table. Therefore, the table is a
prepared persistence structure rather than an actively written audit log in
the current API implementation.

### 3.5 `available_inventory` view

The SQLite view joins `inventory`, `brands`, and `car_models`, and returns only
rows whose status is `available`. It is a convenient read model for public
catalog queries:

```text
inventory --> brands
          --> car_models
```

The API currently performs equivalent joins directly in its SQL queries.

---

## 4. Full MySQL schema

`database/mysql_schema.sql` defines a more complete relational design for
database coursework and a fuller production-style deployment. It creates the
database:

```text
used_car_db
```

This schema is separate from the smaller runtime schema described above. It
uses business-oriented string IDs such as `CAR_123`, whereas the backend
runtime inventory adapter uses numeric IDs such as `123`.

### 4.1 `CAR`

`CAR` is the central table in the full MySQL design.

| Column | Meaning |
|---|---|
| `car_id` | String primary key |
| `brand`, `model` | Vehicle identity |
| `year` | Manufacturing year |
| `fuel_type`, `transmission` | Vehicle specifications |
| `km_driven` | Mileage |
| `purchase_price` | Price paid or acquisition price |
| `status` | `available`, `reserved`, `sold`, or `archived` |
| `created_at`, `updated_at` | Audit timestamps |

Constraints ensure that the year is between 1900 and 2100 and that the price
is non-negative.

Indexes support:

- brand/model searches,
- year searches,
- status/price searches.

### 4.2 `OWNER`

`OWNER` stores the seller or previous-owner information associated with a car.

| Column | Meaning |
|---|---|
| `owner_id` | Primary key |
| `name` | Owner name |
| `contact` | Contact information |
| `car_id` | Foreign key to `CAR` |

The foreign key uses `ON DELETE CASCADE`, so deleting a car deletes its owner
row as well.

### 4.3 `APPRAISAL`

`APPRAISAL` stores one or more valuation records for a car.

| Column | Meaning |
|---|---|
| `appraisal_id` | Primary key |
| `car_id` | Foreign key to `CAR` |
| `appraisal_date` | Date of valuation |
| `predicted_price` | ML or estimated price |
| `final_price` | Human-approved/final price, if available |
| `model_version` | Model identifier used for prediction |

Multiple appraisal rows can exist for one car. This makes it possible to retain
valuation history rather than overwriting old predictions.

### 4.4 `SERVICE_HISTORY`

`SERVICE_HISTORY` stores structured maintenance events in the full MySQL
design.

| Column | Meaning |
|---|---|
| `service_id` | Primary key |
| `car_id` | Foreign key to `CAR` |
| `service_date` | Date of service |
| `service_cost` | Cost of the service |

The current FastAPI implementation stores service history in CouchDB instead;
this MySQL table documents the normalized relational alternative.

### 4.5 `INSURANCE`

`INSURANCE` stores insurance-policy details.

| Column | Meaning |
|---|---|
| `insurance_id` | Primary key |
| `car_id` | Foreign key to `CAR` |
| `policy_number` | Unique policy number |
| `insurer` | Insurance company |
| `policy_type` | Comprehensive, third-party, etc. |
| `start_date`, `expiry_date` | Policy validity period |

The schema checks that the expiry date is not before the start date.

### 4.6 `REGISTRATION`

`REGISTRATION` stores government registration details.

| Column | Meaning |
|---|---|
| `registration_id` | Primary key |
| `car_id` | Unique foreign key to `CAR` |
| `registration_number` | Unique vehicle registration number |
| `registration_date` | Registration date |
| `rto_code` | Regional transport office code |
| `registration_state` | State of registration |
| `registration_type` | Registration category |

Because `car_id` is unique in this table, the full design models one
registration record per car.

### 4.7 MySQL view, procedure, function, and triggers

#### `vw_car_inventory`

This view gives a denormalized inventory read model. It combines:

- core car fields from `CAR`,
- owner name/contact from `OWNER`,
- registration number from `REGISTRATION`,
- the latest appraisal price from `APPRAISAL`.

The latest appraisal is selected by descending `appraisal_date`, with
`appraisal_id` as a tie-breaker.

#### `sp_get_cars_by_budget(max_price)`

This stored procedure returns available cars whose `purchase_price` is less
than or equal to the requested budget, ordered from cheapest to most
expensive.

Example:

```sql
CALL sp_get_cars_by_budget(1000000);
```

#### `fn_car_age(car_year)`

This deterministic function calculates:

```text
current calendar year - car_year
```

#### `trg_car_validate_insert`

This `BEFORE INSERT` trigger rejects a negative purchase price. The table
constraint already expresses the same rule, so the trigger provides an
explicit database-level validation message.

#### `trg_car_default_appraisal`

This `AFTER INSERT` trigger automatically creates an initial appraisal using
the car’s purchase price and the model version `inventory-initial`.

The trigger demonstrates an important database concept: inserting one business
entity can automatically create a related history/default record.

---

## 5. CouchDB configuration

CouchDB is configured through:

```env
COUCHDB_URL=http://127.0.0.1:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=change-me
COUCHDB_CAR_DATABASE=used_car
```

The setup script `database/couchdb_schema.sh` creates two CouchDB databases:

1. `used_car`
2. `used_car_service_history`

CouchDB is document-oriented. Unlike MySQL, it does not require every record
to have the same columns. Each record is a JSON document identified by `_id`
and tracked internally by a revision value (`_rev`).

### 5.1 `used_car` database

This database holds flexible metadata for a car. The API writes documents with
the following shape:

```json
{
  "_id": "CAR_42",
  "car_id": "CAR_42",
  "current_condition": "good",
  "additional_features": ["sunroof", "reverse camera"],
  "accident_history": "none"
}
```

The metadata fields are defined by the Pydantic `CarMetadata` model:

- `current_condition`
- `additional_features`
- `accident_history`

These are a good fit for CouchDB because the metadata can evolve without
altering a relational table. For example, a future document could contain
additional inspection fields while older documents remain valid.

### 5.2 `used_car_service_history` database

Each service event is stored as a separate document:

```json
{
  "_id": "SERVICE_42_1",
  "service_id": "SERVICE_42_1",
  "car_id": "CAR_42",
  "service_date": "2025-03-10",
  "service_cost": 4500,
  "service_details": "Engine oil and filter replaced"
}
```

The document stores `car_id` as the application-level link to the car
metadata document and to the relational inventory row.

One car can have many service documents:

```text
CAR_42
  |
  +--> SERVICE_42_1
  +--> SERVICE_42_2
  +--> SERVICE_42_3
```

This is a logical relationship rather than a database-enforced foreign key.
The backend maintains the convention.

### 5.3 CouchDB indexes

The setup script creates Mango JSON indexes:

- `car-id`: indexes `car_id`.
- `service-id`: indexes `service_id`.
- `service-car-date`: indexes `(car_id, service_date)`.

The backend uses the CouchDB `_find` endpoint with a selector such as:

```json
{
  "selector": {
    "car_id": "CAR_42"
  }
}
```

This retrieves all service records for one car without scanning every
document.

---

## 6. How the two databases are connected

The databases are connected by a naming convention based on the relational
inventory ID:

```text
Relational inventory.id = 42
        |
        +--> CouchDB car_id = CAR_42
        |
        +--> CouchDB service documents car_id = CAR_42
```

There is no cross-database foreign-key constraint. The FastAPI service acts as
the integration layer.

### Reading a car detail page

`GET /api/inventory/{item_id}/details` performs these steps:

1. Query the relational database for the inventory row and joined brand/model.
2. Convert the numeric ID to a CouchDB key such as `CAR_42`.
3. Read the metadata document from `used_car`.
4. Query `used_car_service_history` for documents whose `car_id` is `CAR_42`.
5. Return one combined JSON response:

```json
{
  "inventory": {},
  "car_metadata": {},
  "service_history": []
}
```

If CouchDB is not configured, the endpoint still returns the relational
inventory data, with `car_metadata: null` and an empty service-history list.

---

## 7. Main write and read flows

### 7.1 Appraisal flow

1. The frontend submits brand, model, year, mileage, transmission, owner, and
   fuel type to `POST /api/appraisals`.
2. Pydantic validates the input.
3. `backend/ml.py` loads `used_cars_knn_model.pkl` if available.
4. Input field names are converted to the names expected by the trained
   pipeline.
5. The model returns an estimated price.
6. If the artifact or model dependencies are unavailable, the code returns a
   deterministic fallback estimate.
7. The API returns the estimate, currency, model-loaded flag, and confidence
   label.

The current endpoint does not persist the request in `appraisals`; the
relational table is ready for that future audit-log enhancement.

### 7.2 Catalog flow

1. `GET /api/inventory` accepts optional brand, model, and status filters.
2. The backend joins `inventory`, `brands`, and `car_models`.
3. Results are ordered by newest creation time.
4. `limit` and `offset` implement pagination.
5. A separate count query returns the total number of matching rows.

### 7.3 Admin create flow

`POST /api/admin/inventory` requires HTTP Basic authentication.

1. The backend creates or finds the relational brand and model.
2. It inserts the main inventory row.
3. It creates a CouchDB metadata document named `CAR_<inventory_id>`.
4. Each supplied service record is written as a separate service document.
5. The created relational inventory object is returned.

This is a coordinated application-level write across two databases. It is not
a distributed transaction: if a later CouchDB write fails after the
relational insert succeeds, the two systems can temporarily be inconsistent.
Production code could address this with retries, an outbox/event queue, or a
reconciliation job.

### 7.4 Admin update and delete flow

- `PATCH /api/inventory/{item_id}` updates relational inventory fields.
- `PUT /api/admin/inventory/{item_id}/metadata` replaces/updates the CouchDB
  metadata document.
- `POST /api/admin/inventory/{item_id}/service` appends a service document.
- `DELETE /api/admin/inventory/{item_id}` deletes the relational inventory
  record.

The current delete endpoint does not delete the associated CouchDB documents.
This leaves historical documents available, but it also means orphaned
documents are possible and should be handled by a future cleanup policy if
hard deletion is required.

---

## 8. Initialization and seed data

### SQLite

On first startup:

1. The schema is created.
2. `used_cars_dataset_v2.csv` is read.
3. distinct brand/model pairs are inserted into `brands` and `car_models`.

### MySQL runtime adapter

On first startup:

1. `brands`, `car_models`, and `inventory` are created if absent.
2. The CSV seeds reference data.
3. Up to 100 valid dataset rows are inserted as available inventory.

### Full MySQL schema

The coursework schema is applied separately:

```bash
mysql -u root -p < database/mysql_schema.sql
```

The optional application user can be created with:

```bash
sudo mysql < database/create_app_user.sql
```

### CouchDB

The two databases and indexes can be initialized with:

```bash
COUCHDB_URL=http://127.0.0.1:5984 \
COUCHDB_USER=admin \
COUCHDB_PASSWORD=your-password \
./database/couchdb_schema.sh
```

The FastAPI startup hook also attempts to initialize CouchDB when
`COUCHDB_URL` is set.

---

## 9. Important design observations

### Normalized versus flexible data

The relational side is normalized:

- brand names are stored once,
- models refer to brands by foreign key,
- inventory refers to both by ID,
- joins reconstruct readable responses.

CouchDB is intentionally flexible:

- metadata is stored as a JSON document,
- service records can evolve independently,
- application-level `car_id` links documents to a car.

### Two MySQL representations

There are two representations in this repository:

- The **runtime API schema** uses `brands`, `car_models`, `inventory`, and
  `appraisals`, with numeric IDs.
- The **full coursework schema** uses `CAR`, `OWNER`, `APPRAISAL`,
  `SERVICE_HISTORY`, `INSURANCE`, and `REGISTRATION`, with string business IDs.

They should not be assumed to be automatically synchronized. The runtime
FastAPI queries target the lowercase runtime tables, while the full schema is
an expanded standalone relational design.

### Current source of truth

For the running FastAPI application:

- inventory listing data comes from the relational adapter,
- car metadata and service history come from CouchDB when configured,
- appraisal output comes from the ML model or fallback formula,
- CSV files are seed/training inputs, not live databases.

---

## 10. Useful study queries

### Runtime relational database

```sql
SELECT b.name AS brand, m.name AS model, i.asking_price, i.status
FROM inventory i
JOIN brands b ON b.id = i.brand_id
JOIN car_models m ON m.id = i.model_id
WHERE i.status = 'available'
ORDER BY i.asking_price;
```

```sql
SELECT b.name, COUNT(*) AS available_count
FROM inventory i
JOIN brands b ON b.id = i.brand_id
WHERE i.status = 'available'
GROUP BY b.name
ORDER BY available_count DESC;
```

### Full MySQL database

```sql
SELECT * FROM vw_car_inventory;
```

```sql
SELECT car_id, fn_car_age(year) AS age
FROM CAR
WHERE status = 'available';
```

```sql
CALL sp_get_cars_by_budget(1000000);
```

### CouchDB REST concepts

```text
GET  /used_car/CAR_42
POST /used_car_service_history/_find
PUT  /used_car/CAR_42
```

The service uses CouchDB revisions for document updates. A client that updates
an existing document normally needs to preserve the current `_rev`.

---

## 11. Short summary

The project uses the relational database for data that benefits from strict
structure, constraints, joins, indexes, and transactions. It uses CouchDB for
car-specific metadata and a growing list of service records that benefit from
JSON flexibility. FastAPI combines the two sources into the responses consumed
by the frontend, while the KNN model supplies the valuation estimate.

