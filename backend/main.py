import os
import secrets
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .database import init_db, query
from .couchdb import get_couchdb_client, initialize_couchdb
from .config import ADMIN_PASSWORD, ADMIN_USERNAME, COUCHDB_CAR_DATABASE, COUCHDB_URL
from .ml import predict, load_model
from .models import AppraisalRequest, AppraisalResponse, InventoryCreate, InventoryItem, InventoryUpdate, ServiceRecord

app = FastAPI(title="Used Car Appraisal API", version="1.0.0")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
basic_auth = HTTPBasic(auto_error=False)

def require_admin(credentials: HTTPBasicCredentials | None = Depends(basic_auth)) -> None:
    if (
        not ADMIN_PASSWORD
        or credentials is None
        or not secrets.compare_digest(credentials.username, ADMIN_USERNAME)
        or not secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

@app.on_event("startup")
def startup():
    init_db()
    if COUCHDB_URL:
        initialize_couchdb()

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": load_model() is not None,
        "couchdb_configured": bool(COUCHDB_URL),
    }

@app.post("/api/appraisals", response_model=AppraisalResponse)
def appraise(request: AppraisalRequest):
    price, loaded = predict(request.model_dump())
    return AppraisalResponse(estimated_price=price, model_loaded=loaded, confidence="model" if loaded else "fallback")

@app.get("/api/brands")
def brands(): return query("SELECT id, name FROM brands ORDER BY name", fetch=True)

@app.get("/api/brands/{brand}/models")
def brand_models(brand: str):
    rows = query("SELECT m.id, b.name AS brand, m.name FROM car_models m JOIN brands b ON b.id=m.brand_id WHERE lower(b.name)=lower(?) ORDER BY m.name", (brand,), True)
    return rows

@app.get("/api/inventory")
def list_inventory(brand: Optional[str]=None, model: Optional[str]=None, status: Optional[str]=None, limit: int=Query(50, ge=1, le=500), offset: int=Query(0, ge=0)):
    conditions, params = [], []
    for col, value in (("b.name", brand), ("m.name", model), ("i.status", status)):
        if value: conditions.append(f"lower({col})=lower(?)"); params.append(value)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    base = "FROM inventory i JOIN brands b ON b.id=i.brand_id JOIN car_models m ON m.id=i.model_id"
    items = query(f"SELECT i.id,b.name brand,m.name model,i.year,i.km_driven,i.transmission,i.owner,i.fuel_type,i.asking_price,i.status,i.description,i.registration_no {base}{where} ORDER BY i.created_at DESC LIMIT ? OFFSET ?", (*params,limit,offset), True)
    total = query(f"SELECT COUNT(*) count {base}{where}", tuple(params), True)[0]["count"]
    return {"items": items, "total": total, "limit": limit, "offset": offset}

def _create_inventory(item: InventoryItem):
    try:
        brand = query("INSERT OR IGNORE INTO brands(name) VALUES (?)", (item.brand.strip(),))
        b = query("SELECT id FROM brands WHERE lower(name)=lower(?)", (item.brand,), True)[0]["id"]
        query("INSERT OR IGNORE INTO car_models(brand_id,name) VALUES (?,?)", (b,item.model.strip()))
        m = query("SELECT id FROM car_models WHERE brand_id=? AND lower(name)=lower(?)", (b,item.model), True)[0]["id"]
        ident = query("INSERT INTO inventory(brand_id,model_id,year,km_driven,transmission,owner,fuel_type,asking_price,status,description,registration_no) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (b,m,item.year,item.km_driven,item.transmission,item.owner,item.fuel_type,item.asking_price,item.status,item.description,item.registration_no))
        return {**item.model_dump(), "id": ident}
    except Exception as exc: raise HTTPException(400, str(exc))

@app.post("/api/admin/inventory", status_code=201)
def create_admin_inventory(item: InventoryCreate, _: None = Depends(require_admin)):
    result = _create_inventory(item)
    client = get_couchdb_client()
    if not client:
        raise HTTPException(503, "CouchDB is not configured")
    car_id = f"CAR_{result['id']}"
    client.put_document(
        COUCHDB_CAR_DATABASE,
        car_id,
        {"_id": car_id, "car_id": car_id, **item.metadata.model_dump()},
    )
    for index, service in enumerate(item.service_history, start=1):
        service_id = f"SERVICE_{result['id']}_{index}"
        client.put_document(
            client.service_database,
            service_id,
            {
                "_id": service_id,
                "service_id": service_id,
                "car_id": car_id,
                **service.model_dump(),
            },
        )
    return result

@app.get("/api/inventory/{item_id}/details")
def inventory_details(item_id: int):
    rows = query(
        "SELECT i.id,b.name brand,m.name model,i.year,i.km_driven,i.transmission,"
        "i.owner,i.fuel_type,i.asking_price,i.status,i.description,i.registration_no "
        "FROM inventory i JOIN brands b ON b.id=i.brand_id JOIN car_models m ON m.id=i.model_id "
        "WHERE i.id=?",
        (item_id,),
        True,
    )
    if not rows:
        raise HTTPException(404, "Inventory item not found")
    client = get_couchdb_client()
    if not client:
        return {"inventory": rows[0], "car_metadata": None, "service_history": []}
    car_id = f"CAR_{item_id}"
    metadata = client.get_document(COUCHDB_CAR_DATABASE, car_id)
    services = client.find(client.service_database, {"car_id": car_id})
    return {"inventory": rows[0], "car_metadata": metadata, "service_history": services}

@app.put("/api/admin/inventory/{item_id}/metadata")
def update_car_metadata(
    item_id: int,
    metadata: dict,
    _: None = Depends(require_admin),
):
    if not query("SELECT id FROM inventory WHERE id=?", (item_id,), True):
        raise HTTPException(404, "Inventory item not found")
    client = get_couchdb_client()
    if not client:
        raise HTTPException(503, "CouchDB is not configured")
    car_id = f"CAR_{item_id}"
    document = {"_id": car_id, "car_id": car_id, **metadata}
    return client.put_document(COUCHDB_CAR_DATABASE, car_id, document)

@app.post("/api/admin/inventory/{item_id}/service", status_code=201)
def add_service_history(
    item_id: int,
    service: ServiceRecord,
    _: None = Depends(require_admin),
):
    if not query("SELECT id FROM inventory WHERE id=?", (item_id,), True):
        raise HTTPException(404, "Inventory item not found")
    client = get_couchdb_client()
    if not client:
        raise HTTPException(503, "CouchDB is not configured")
    service_id = f"SERVICE_{item_id}_{int(__import__('time').time() * 1000)}"
    document = {
        "_id": service_id,
        "service_id": service_id,
        "car_id": f"CAR_{item_id}",
        **service.model_dump(),
    }
    return client.put_document(client.service_database, service_id, document)

@app.patch("/api/inventory/{item_id}")
def update_inventory(item_id: int, update: InventoryUpdate):
    values = update.model_dump(exclude_unset=True)
    if not values: raise HTTPException(400, "No fields supplied")
    fields = ",".join(f"{k}=?" for k in values)
    changed = query(f"UPDATE inventory SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE id=?", (*values.values(),item_id))
    if not changed: raise HTTPException(404, "Inventory item not found")
    return query("SELECT * FROM inventory WHERE id=?", (item_id,), True)[0]

@app.delete("/api/admin/inventory/{item_id}", status_code=204)
def delete_inventory(item_id: int, _: None = Depends(require_admin)):
    if not query("DELETE FROM inventory WHERE id=?", (item_id,)): raise HTTPException(404, "Inventory item not found")
