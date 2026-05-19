"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class ClientRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    company: Optional[str] = Field(None, max_length=100)
    token_validity_days: int = Field(365, ge=1, le=730)
    invite_code: Optional[str] = Field("", description="Code d'invitation requis")


    class Config:
        json_schema_extra = {
            "example": {
                "name": "Alice Martin",
                "email": "alice@acmecorp.com",
                "company": "Acme Corp",
                "token_validity_days": 365,
                "invite_code": "mon-code-secret",
            }
        }


class ClientResponse(BaseModel):
    client_id: str
    name: str
    email: str
    company: Optional[str]
    api_token: str
    token_expires_at: Optional[datetime]
    created_at: datetime
    predictions_count: int

    class Config:
        from_attributes = True


class ClientProfile(BaseModel):
    client_id: str
    name: str
    email: str
    company: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    predictions_count: int
    token_expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class ChurnPredictionInput(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=100)
    tenure_months: int = Field(..., ge=0, le=240, description="Months as customer")
    monthly_charges: float = Field(..., ge=0, le=500, description="Monthly bill in USD")
    total_charges: float = Field(..., ge=0, description="Total charges to date")
    num_products: int = Field(
        ..., ge=1, le=10, description="Number of products subscribed"
    )
    has_internet: bool = Field(..., description="Has internet service")
    has_phone: bool = Field(..., description="Has phone service")
    contract_type: int = Field(
        ..., ge=0, le=2, description="0=Month-to-Month, 1=One Year, 2=Two Year"
    )
    payment_method: int = Field(
        ...,
        ge=0,
        le=3,
        description="0=Electronic, 1=Mailed Check, 2=Bank Transfer, 3=Credit Card",
    )
    paperless_billing: bool = Field(..., description="Uses paperless billing")
    tech_support: bool = Field(..., description="Has tech support")
    online_security: bool = Field(..., description="Has online security service")
    num_support_tickets: int = Field(
        ..., ge=0, le=50, description="Support tickets opened"
    )
    avg_monthly_long_distance: float = Field(
        ..., ge=0, description="Avg monthly long distance usage"
    )
    days_since_last_interaction: int = Field(
        ..., ge=0, le=3650, description="Days since last customer interaction"
    )

    @validator("total_charges")
    def total_must_be_gte_monthly(cls, v, values):
        if "monthly_charges" in values and v < values["monthly_charges"] * 0:
            raise ValueError("Total charges cannot be negative")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "Jean Dupont",
                "tenure_months": 8,
                "monthly_charges": 89.5,
                "total_charges": 716.0,
                "num_products": 2,
                "has_internet": True,
                "has_phone": True,
                "contract_type": 0,
                "payment_method": 0,
                "paperless_billing": True,
                "tech_support": False,
                "online_security": False,
                "num_support_tickets": 5,
                "avg_monthly_long_distance": 12.5,
                "days_since_last_interaction": 45,
            }
        }


class ChurnPredictionOutput(BaseModel):
    prediction_id: int
    customer_name: Optional[str]
    churn_probability: float
    churn_prediction: bool
    risk_level: str
    risk_color: str
    recommendation: str
    key_factors: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BatchPredictionInput(BaseModel):
    customers: List[ChurnPredictionInput] = Field(..., max_items=50)


class PredictionHistory(BaseModel):
    predictions: List[ChurnPredictionOutput]
    total: int
    page: int
    page_size: int


class TokenRefreshResponse(BaseModel):
    new_token: str
    expires_at: datetime
    message: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str
    timestamp: datetime
