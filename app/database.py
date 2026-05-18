"""
Database configuration using SQLAlchemy with SQLite (easily swappable to PostgreSQL)
"""

import os
import pathlib
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/churn.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    company = Column(String, nullable=True)
    api_token = Column(String, unique=True, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    predictions_count = Column(Integer, default=0)
    predictions = relationship(
        "Prediction", back_populates="client", cascade="all, delete-orphan"
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("clients.client_id"), nullable=False)
    customer_name = Column(String, nullable=True)
    tenure_months = Column(Integer)
    monthly_charges = Column(Float)
    total_charges = Column(Float)
    num_products = Column(Integer)
    has_internet = Column(Boolean)
    has_phone = Column(Boolean)
    contract_type = Column(Integer)
    payment_method = Column(Integer)
    paperless_billing = Column(Boolean)
    tech_support = Column(Boolean)
    online_security = Column(Boolean)
    num_support_tickets = Column(Integer)
    avg_monthly_long_distance = Column(Float)
    days_since_last_interaction = Column(Integer)
    churn_probability = Column(Float)
    churn_prediction = Column(Boolean)
    risk_level = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    client = relationship("Client", back_populates="predictions")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import pathlib

    data_dir = pathlib.Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
