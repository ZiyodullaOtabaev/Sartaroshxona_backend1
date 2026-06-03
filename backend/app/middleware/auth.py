"""
Authentication & Authorization middleware
JWT token tekshirish va foydalanuvchi huquqlarini nazorat qilish
"""
import datetime
import jwt
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_hours: int = 24) -> str:
    """JWT token yaratish"""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=expires_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Token'ni tekshirish va payload qaytarish"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token muddati tugagan. Qayta login qiling.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict | None:
    """
    Optional auth — token bor bo'lsa tekshiradi, yo'q bo'lsa None qaytaradi.
    Public endpointlar uchun.
    """
    if credentials is None:
        return None
    return verify_token(credentials.credentials)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Majburiy auth — token bo'lmasa 401 xato beradi.
    Protected endpointlar uchun.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Avtorizatsiya talab qilinadi. Token yuboring.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


async def require_barber(current_user: dict = Depends(require_auth)) -> dict:
    """Faqat barber role uchun"""
    if current_user.get("role") != "barber":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat sartaroshlar uchun",
        )
    return current_user


async def require_customer(current_user: dict = Depends(require_auth)) -> dict:
    """Faqat customer role uchun"""
    if current_user.get("role") != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat mijozlar uchun",
        )
    return current_user
