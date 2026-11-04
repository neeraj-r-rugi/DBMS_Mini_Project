from typing import Any, Dict, List, Optional
try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:
    class BaseModel: pass
    def Field(default=None, **kwargs): return default

class AppraisalRequest(BaseModel):
    brand: str
    model: str
    year: int = Field(..., ge=1900, le=2100)
    km_driven: float = Field(..., ge=0)
    transmission: str = "manual"
    owner: str = "first"
    fuel_type: str = "petrol"

class AppraisalResponse(BaseModel):
    estimated_price: float
    currency: str = "INR"
    model_loaded: bool
    confidence: Optional[str] = None

class Brand(BaseModel):
    id: Optional[int] = None
    name: str

class ModelInfo(BaseModel):
    id: Optional[int] = None
    brand: str
    name: str

class InventoryItem(BaseModel):
    id: Optional[int] = None
    brand: str
    model: str
    year: int = Field(..., ge=1900, le=2100)
    km_driven: float = Field(..., ge=0)
    transmission: str = "manual"
    owner: str = "first"
    fuel_type: str = "petrol"
    asking_price: float = Field(..., ge=0)
    status: str = "available"
    description: Optional[str] = None
    registration_no: Optional[str] = None

class InventoryUpdate(BaseModel):
    asking_price: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    description: Optional[str] = None
    km_driven: Optional[float] = Field(None, ge=0)

class CarMetadata(BaseModel):
    current_condition: str = "not provided"
    additional_features: List[str] = Field(default_factory=list)
    accident_history: str = "not provided"

class ServiceRecord(BaseModel):
    service_date: str
    service_cost: float = Field(..., ge=0)
    service_details: str

class InventoryCreate(InventoryItem):
    metadata: CarMetadata = Field(default_factory=CarMetadata)
    service_history: List[ServiceRecord] = Field(default_factory=list)

class InventoryPage(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
