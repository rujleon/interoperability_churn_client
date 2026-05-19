"""
Security module: Token generation, validation, rate limiting, and auth
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import Client, get_db

API_KEY_HEADER = APIKeyHeader(name="X-API-Token", auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    import warnings
    SECRET_KEY = secrets.token_hex(32)
    warnings.warn(
        "⚠️  SECRET_KEY non définie ! Les tokens seront invalidés à chaque redémarrage.",
        RuntimeWarning
    )

# ✅ AJOUT : contrôle des inscriptions
REGISTRATION_CODE = os.getenv("REGISTRATION_CODE", "")
REGISTRATION_OPEN = os.getenv("REGISTRATION_OPEN", "true").lower() == "true"

# In-memory rate limiter
_rate_limit_store = defaultdict(list)
_rate_limit_lock = threading.Lock()

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))


# ✅ AJOUT : fonction de vérification d'inscription
def check_registration_allowed(invite_code: str = "") -> None:
    """Vérifie si l'inscription est autorisée"""
    if not REGISTRATION_OPEN:
        raise HTTPException(
            status_code=403,
            detail="Les inscriptions sont fermées. Contactez l'administrateur."
        )
    if REGISTRATION_CODE and invite_code != REGISTRATION_CODE:
        raise HTTPException(
            status_code=403,
            detail="Code d'invitation invalide ou manquant."
        )


def generate_api_token() -> str:
    raw = secrets.token_bytes(32)
    signature = hmac.new(SECRET_KEY.encode(), raw, hashlib.sha256).digest()
    combined = raw + signature
    return "churn_" + combined.hex()


def validate_token_format(token: str) -> bool:
    if not token or not token.startswith("churn_"):
        return False
    try:
        hex_part = token[6:]
        combined = bytes.fromhex(hex_part)
        if len(combined) != 64:
            return False
        raw = combined[:32]
        provided_sig = combined[32:]
        expected_sig = hmac.new(SECRET_KEY.encode(), raw, hashlib.sha256).digest()
        return hmac.compare_digest(provided_sig, expected_sig)
    except Exception:
        return False


def check_rate_limit(client_id: str) -> bool:
    now = time.time()
    with _rate_limit_lock:
        _rate_limit_store[client_id] = [
            r for r in _rate_limit_store[client_id] if now - r < RATE_LIMIT_WINDOW
        ]
        if len(_rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
            return False
        _rate_limit_store[client_id].append(now)
        return True


def get_remaining_requests(client_id: str) -> int:
    now = time.time()
    with _rate_limit_lock:
        requests = [
            r for r in _rate_limit_store[client_id] if now - r < RATE_LIMIT_WINDOW
        ]
        return max(0, RATE_LIMIT_REQUESTS - len(requests))


async def get_current_client(
    request: Request,
    token: Optional[str] = Security(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> Client:
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing API token. Include 'X-API-Token' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not validate_token_format(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid token format or signature.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    client = (
        db.query(Client)
        .filter(Client.api_token == token, Client.is_active == True)
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=401,
            detail="Token not found or account deactivated.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if client.token_expires_at and client.token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=401,
            detail="Token expired. Please regenerate your token.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not check_rate_limit(client.client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per hour.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )
    client.last_login = datetime.utcnow()
    db.commit()
    return client


async def get_admin_client(client: Client = Depends(get_current_client)) -> Client:
    if not getattr(client, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return client