# Guide.md: Used Car Appraisal and Management System

This guide outlines the complete blueprint for an autonomous agent or developer to build the **Used Car Appraisal and Management System** from scratch, adhering to all specified database, backend, frontend, and machine learning constraints.

---

## 1. Project Overview & Architecture

The system consists of three core modules:

1. **Car Appraisal Module (Any User)**: Users select a car brand and model from an allowed list, input car specifications (`Year`, `kmDriven`, `Transmission`, `Owner`, `FuelType`), and get an instant predicted price via the integrated machine learning pipeline (`model.py`).


2. **Inventory Management System (Admin)**: Admins can add, update, and track cars in the lot, managing related records like insurance, registration, service histories, and owner information.


3. **Public Car Catalog & Filter (Any User)**: Prospective buyers can browse all available cars in the lot and filter them based on preferences (brand, model, budget, fuel type, transmission).

### High-Level Architecture

```
[ Next.js Frontend (UI) ] 
       │
       ▼ (HTTP / JSON API)
[ Python FastAPI Backend ] ◄──► [ ML Model (used_cars_knn_model.pkl) ]
       │                   
       ├──────► [ MySQL Database ] (Relational Tables + Advanced Features)
       └──────► [ Apache CouchDB ] (Documents for Conditions & Service Details)

```

---

## 2. Tech Stack & Prerequisites

* **Frontend**: Next.js (App Router), Tailwind CSS, TypeScript
* **Backend**: Python (FastAPI, Uvicorn, Scikit-learn, Joblib, Pandas)


* **Relational Database**: MySQL (Tables, foreign keys, advanced features)


* **NoSQL Database**: Apache CouchDB (Car conditions, accident history, detailed service notes)



---

## 3. Database Setup (MySQL + Apache CouchDB)

### Part A: MySQL Schema & Advanced Features

Implement the relational schema provided in `Schema.md`. To satisfy the constraint of implementing **at least 4 advanced database features**, we will include:

1. **Indexing**: Performance indexes on `CAR(brand)`, `CAR(model)`, and `CAR(year)`.
2. **View**: A summary view `vw_car_inventory` that aggregates car details with their latest predicted appraisal price and owner info.
3. **Stored Procedure**: `sp_get_cars_by_budget` to filter cars under a specific price threshold.
4. **Trigger**: `trg_after_car_insert` to log or initialize default states upon car insertion.

```sql
-- Create Database
CREATE DATABASE used_car_db;
USE used_car_db;

-- 1. CAR Table
CREATE TABLE CAR (
    car_id VARCHAR(50) PRIMARY KEY,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    fuel_type VARCHAR(30) NOT NULL,
    transmission VARCHAR(30) NOT NULL,
    km_driven INT NOT NULL,
    purchase_price DECIMAL(12,2) NOT NULL
);

-- 2. OWNER Table
CREATE TABLE OWNER (
    owner_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact VARCHAR(50) NOT NULL,
    car_id VARCHAR(50),
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

-- 3. APPRAISAL Table
CREATE TABLE APPRAISAL (
    appraisal_id VARCHAR(50) PRIMARY KEY,
    car_id VARCHAR(50),
    appraisal_date DATE NOT NULL,
    predicted_price DECIMAL(12,2) NOT NULL,
    final_price DECIMAL(12,2),
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

-- 4. SERVICE_HISTORY Table
CREATE TABLE SERVICE_HISTORY (
    service_id VARCHAR(50) PRIMARY KEY,
    car_id VARCHAR(50),
    service_date DATE NOT NULL,
    service_cost DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

-- 5. INSURANCE Table
CREATE TABLE INSURANCE (
    insurance_id VARCHAR(50) PRIMARY KEY,
    car_id VARCHAR(50),
    policy_number VARCHAR(100) UNIQUE NOT NULL,
    insurer VARCHAR(100) NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

-- 6. REGISTRATION Table
CREATE TABLE REGISTRATION (
    registration_id VARCHAR(50) PRIMARY KEY,
    car_id VARCHAR(50) UNIQUE,
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    registration_date DATE NOT NULL,
    rto_code VARCHAR(20) NOT NULL,
    registration_state VARCHAR(50) NOT NULL,
    registration_type VARCHAR(50) NOT NULL,
    FOREIGN KEY (car_id) REFERENCES CAR(car_id) ON DELETE CASCADE
);

-- ADVANCED FEATURE 1: Indexing
CREATE INDEX idx_car_brand_model ON CAR(brand, model);
CREATE INDEX idx_car_year ON CAR(year);

-- ADVANCED FEATURE 2: View
CREATE VIEW vw_car_inventory AS
SELECT 
    c.car_id, c.brand, c.model, c.year, c.fuel_type, c.transmission, c.km_driven, c.purchase_price,
    o.name AS owner_name, o.contact AS owner_contact,
    r.registration_number
FROM CAR c
LEFT JOIN OWNER o ON c.car_id = o.car_id
LEFT JOIN REGISTRATION r ON c.car_id = r.car_id;

-- ADVANCED FEATURE 3: Stored Procedure
DELIMITER //
CREATE PROCEDURE sp_get_cars_by_budget(IN max_price DECIMAL(12,2))
BEGIN
    SELECT * FROM CAR WHERE purchase_price <= max_price;
END //
DELIMITER ;

-- ADVANCED FEATURE 4: Trigger
DELIMITER //
CREATE TRIGGER trg_after_car_insert
AFTER INSERT ON CAR
FOR EACH ROW
BEGIN
    -- Optional logging or default appraisal initialization action
    INSERT INTO APPRAISAL (appraisal_id, car_id, appraisal_date, predicted_price, final_price)
    VALUES (CONCAT('APP_', NEW.car_id), NEW.car_id, CURDATE(), NEW.purchase_price, NEW.purchase_price);
END //
DELIMITER ;

```

### Part B: CouchDB Documents

As specified in `Schema.md`, CouchDB handles unstructured or descriptive components:

* **`Car` Collection**: Stores `car_id`, `current_condition`, `additional_features` (array), and `accident_history`.
* **`ServiceHistory` Collection**: Stores `service_id`, `car_id`, `service_date`, `service_cost`, and `service_details` (detailed text/notes).

---

## 4. Backend Implementation (Python FastAPI)

Create a FastAPI project (`main.py`) that handles:

1. Loading the trained Scikit-Learn KNN model (`used_cars_knn_model.pkl`) generated by `model.py`.


2. Providing endpoints for appraisal prediction.
3. Managing inventory CRUD operations across MySQL and CouchDB.

### `main.py` Skeleton Example

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
pydantic_import = True
import joblib
import pandas as pd
from pydantic import BaseModel

app = FastAPI(title="Used Car Appraisal and Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained KNN model pipeline
try:
    model = joblib.load("used_cars_knn_model.pkl")
except Exception as e:
    model = None

class AppraisalRequest(BaseModel):
    Brand: str
    model: str
    Year: int
    kmDriven: float
    Transmission: str
    Owner: str
    FuelType: str

@app.post("/api/appraise")
def appraise_car(data: AppraisalRequest):
    if not model:
        raise HTTPException(status_code=500, detail="ML Model not loaded.")
    
    input_df = pd.DataFrame([data.dict()])
    # Ensure lowercase standardisation as done in model.py
    for col in ["Brand", "model", "Transmission", "Owner", "FuelType"]:
        input_df[col] = input_df[col].astype(str).str.lower().str.strip()
        
    prediction = model.predict(input_df)[0]
    return {"predicted_price": round(float(prediction), 2)}

@app.get("/api/brands-models")
def get_brands_models():
    # Return allowed brands and models list restricted by dataset scope
    return {
        "toyota": ["corolla", "camry", "innova"],
        "honda": ["civic", "city", "accord"],
        "hyundai": ["i20", "creta", "verna"]
    }

```

---

## 5. Frontend Implementation (Next.js)

Build a clean user interface using Next.js App Router with the following pages:

* `/appraise`: Form for users to select Brand/Model from dropdowns, enter mileage, year, fuel type, and view predicted price.
* `/inventory`: Admin panel to view, add, or edit cars in the lot, syncing relational data with MySQL and metadata with CouchDB.
* `/catalog`: Public listing page allowing users to view available cars in the lot and filter by brand, model, or price range.

---

## 6. Step-by-Step Execution & Testing Plan

1. **Database Initialization**: Execute the MySQL script to create tables, views, indexes, and stored procedures. Run `database/couchdb_schema.sh` to create CouchDB databases and Mango indexes.
2. **Model Training**: Run `model.py` against your dataset to generate `used_cars_knn_model.pkl`.
3. **Backend Launch**: Run FastAPI using `uvicorn main:app --reload`.
4. **Frontend Launch**: Run Next.js using `npm run dev`.
5. **Verification**: Test the appraisal endpoint with sample inputs and verify inventory additions through both MySQL and CouchDB storage.

---