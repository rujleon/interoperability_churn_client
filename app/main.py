"""
Customer Churn Prediction API
FastAPI application with secure token authentication, rate limiting, and ML predictions
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Client, Prediction, get_db, init_db
from app.predictor import predictor
from app.schemas import (
    BatchPredictionInput,
    ChurnPredictionInput,
    ChurnPredictionOutput,
    ClientProfile,
    ClientRegister,
    ClientResponse,
    HealthResponse,
    TokenRefreshResponse,
)
from app.security import generate_api_token, get_current_client, get_remaining_requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Churn Prediction API...")
    init_db()
    try:
        predictor.load()
        logger.info("✅ ML Model loaded successfully")
    except FileNotFoundError:
        logger.warning("⚠️  Model not found. Training now...")
        from ml.train_model import train

        train()
        predictor.load()
    yield
    logger.info("👋 Shutting down...")


app = FastAPI(
    title="🔮 Churn Prediction API",
    description="""
## API de Prédiction de Churn Client

Prédisez la probabilité de désabonnement de vos clients grâce à notre modèle ML (Gradient Boosting).

### Authentification
Chaque client reçoit un **token API unique** à inclure dans l'en-tête `X-API-Token`.

### Fonctionnalités
- 🔮 **Prédiction individuelle** de churn avec probabilité et niveau de risque
- 📦 **Prédictions en batch** (jusqu'à 50 clients simultanément)
- 📊 **Historique complet** des prédictions par client
- 🔑 **Renouvellement de token** sécurisé
- ⚡ **Rate limiting** : 100 requêtes / heure par client

### Niveaux de risque
| Probabilité | Niveau | Action |
|---|---|---|
| < 30% | 🟢 Faible | Fidélisation standard |
| 30–50% | 🟡 Modéré | Surveillance |
| 50–75% | 🔴 Élevé | Action immédiate |
| > 75% | ⚫ Critique | Intervention urgente |
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={"name": "Churn API Support", "email": "support@churnapi.io"},
    license_info={"name": "MIT"},
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("/app/static"):
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health and model status"""
    return HealthResponse(
        status="healthy",
        model_loaded=predictor.is_loaded,
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


# ─── CLIENT REGISTRATION ──────────────────────────────────────────────────────


@app.post(
    "/clients/register",
    response_model=ClientResponse,
    tags=["Authentication"],
    status_code=201,
)
async def register_client(data: ClientRegister, db: Session = Depends(get_db)):
    """
    Register a new client and receive a unique API token.

    **Note**: Store your token securely — it won't be shown again after registration.
    """
    # Check email uniqueness
    existing = db.query(Client).filter(Client.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    client_id = f"cli_{uuid.uuid4().hex[:12]}"
    token = generate_api_token()
    expires_at = datetime.utcnow() + timedelta(days=data.token_validity_days)

    client = Client(
        client_id=client_id,
        name=data.name,
        email=data.email,
        company=data.company,
        api_token=token,
        token_expires_at=expires_at,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    logger.info(f"✅ New client registered: {client_id} ({data.email})")
    return client


# ─── CLIENT PROFILE ───────────────────────────────────────────────────────────


@app.get("/clients/me", response_model=ClientProfile, tags=["Authentication"])
async def get_my_profile(client: Client = Depends(get_current_client)):
    """Get your client profile and usage statistics"""
    return client


@app.post(
    "/clients/me/refresh-token",
    response_model=TokenRefreshResponse,
    tags=["Authentication"],
)
async def refresh_token(
    validity_days: int = Query(365, ge=1, le=730),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Generate a new API token.

    ⚠️ **Warning**: Your old token will be immediately invalidated.
    """
    new_token = generate_api_token()
    new_expires = datetime.utcnow() + timedelta(days=validity_days)

    client.api_token = new_token
    client.token_expires_at = new_expires
    db.commit()

    return TokenRefreshResponse(
        new_token=new_token,
        expires_at=new_expires,
        message="Token refreshed successfully. Update your applications immediately.",
    )


# ─── PREDICTIONS ──────────────────────────────────────────────────────────────


@app.post("/predict", response_model=ChurnPredictionOutput, tags=["Predictions"])
async def predict_churn(
    data: ChurnPredictionInput,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Predict churn probability for a single customer.

    Returns a probability score, risk level, recommendation, and key factors.
    """
    features = data.model_dump(exclude={"customer_name"})

    prob, pred, risk_level, risk_color, recommendation, key_factors = predictor.predict(
        features
    )

    prediction_record = Prediction(
        client_id=client.client_id,
        customer_name=data.customer_name,
        churn_probability=round(prob, 4),
        churn_prediction=pred,
        risk_level=risk_level,
        **{k: v for k, v in features.items()},
    )
    db.add(prediction_record)
    client.predictions_count += 1
    db.commit()
    db.refresh(prediction_record)

    return ChurnPredictionOutput(
        prediction_id=prediction_record.id,
        customer_name=data.customer_name,
        churn_probability=round(prob, 4),
        churn_prediction=pred,
        risk_level=risk_level,
        risk_color=risk_color,
        recommendation=recommendation,
        key_factors=key_factors,
        created_at=prediction_record.created_at,
    )


@app.post("/predict/batch", tags=["Predictions"])
async def predict_churn_batch(
    data: BatchPredictionInput,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Predict churn for up to 50 customers in a single request.
    """
    results = []
    for customer in data.customers:
        features = customer.model_dump(exclude={"customer_name"})
        prob, pred, risk_level, risk_color, recommendation, key_factors = (
            predictor.predict(features)
        )

        prediction_record = Prediction(
            client_id=client.client_id,
            customer_name=customer.customer_name,
            churn_probability=round(prob, 4),
            churn_prediction=pred,
            risk_level=risk_level,
            **{k: v for k, v in features.items()},
        )
        db.add(prediction_record)
        client.predictions_count += 1

        results.append(
            {
                "customer_name": customer.customer_name,
                "churn_probability": round(prob, 4),
                "churn_prediction": pred,
                "risk_level": risk_level,
                "risk_color": risk_color,
                "recommendation": recommendation,
                "key_factors": key_factors,
            }
        )

    db.commit()

    summary = {
        "total": len(results),
        "churners": sum(1 for r in results if r["churn_prediction"]),
        "avg_probability": round(
            sum(r["churn_probability"] for r in results) / len(results), 4
        ),
        "by_risk": {
            "Critique": sum(1 for r in results if r["risk_level"] == "Critique"),
            "Élevé": sum(1 for r in results if r["risk_level"] == "Élevé"),
            "Modéré": sum(1 for r in results if r["risk_level"] == "Modéré"),
            "Faible": sum(1 for r in results if r["risk_level"] == "Faible"),
        },
    }

    return {"summary": summary, "predictions": results}


# ─── HISTORY ──────────────────────────────────────────────────────────────────


@app.get("/predictions/history", tags=["Predictions"])
async def get_prediction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get your prediction history with optional filtering"""
    query = db.query(Prediction).filter(Prediction.client_id == client.client_id)

    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level)

    total = query.count()
    predictions = (
        query.order_by(Prediction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "predictions": [
            {
                "id": p.id,
                "customer_name": p.customer_name,
                "churn_probability": p.churn_probability,
                "churn_prediction": p.churn_prediction,
                "risk_level": p.risk_level,
                "created_at": p.created_at,
            }
            for p in predictions
        ],
    }


@app.get("/predictions/stats", tags=["Predictions"])
async def get_my_stats(
    client: Client = Depends(get_current_client), db: Session = Depends(get_db)
):
    """Get aggregated statistics on your predictions"""
    preds = db.query(Prediction).filter(Prediction.client_id == client.client_id).all()

    if not preds:
        return {"message": "No predictions yet", "total": 0}

    probs = [p.churn_probability for p in preds]
    churners = [p for p in preds if p.churn_prediction]

    return {
        "total_predictions": len(preds),
        "total_churners_detected": len(churners),
        "churn_rate": round(len(churners) / len(preds) * 100, 1),
        "avg_churn_probability": round(sum(probs) / len(probs), 4),
        "max_probability": round(max(probs), 4),
        "min_probability": round(min(probs), 4),
        "remaining_requests_this_hour": get_remaining_requests(client.client_id),
        "by_risk_level": {
            level: sum(1 for p in preds if p.risk_level == level)
            for level in ["Faible", "Modéré", "Élevé", "Critique"]
        },
    }


# ─── DASHBOARD HTML ───────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    """Serve the main dashboard"""
    import pathlib

    html_path = (
        pathlib.Path(__file__).resolve().parent.parent / "templates" / "index.html"
    )
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>Churn Prediction API</h1><p><a href='/docs'>API Docs</a></p>"
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
