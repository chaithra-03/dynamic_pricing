# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.user import TokenData

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# Password hashing
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Create Access Token
def create_access_token(data: dict, expires_minutes: Optional[int] = None):
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Create Refresh Token
def create_refresh_token(data: dict, expires_days: int = 7):
    expire = datetime.utcnow() + timedelta(days=expires_days)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Base decode
def _decode_raw(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# Decode Access Token
def decode_access_token(token: str) -> TokenData:
    payload = _decode_raw(token)
    if not payload:
        return TokenData()
    return TokenData(username=payload.get("sub"), role=payload.get("role"))


# Decode Refresh Token
def decode_refresh_token(token: str) -> TokenData:
    payload = _decode_raw(token)
    if not payload:
        return TokenData()
    return TokenData(username=payload.get("sub"), role=payload.get("role"))


# Generic token decoder (OPTIONAL)
def decode_token(token: str) -> Optional[dict]:
    return _decode_raw(token)
