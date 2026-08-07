from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

security = HTTPBearer(auto_error=False)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().app_secret, salt="allie-auth")


def create_token() -> str:
    return _serializer().dumps({"sub": "allie"})


def verify_token(token: str) -> bool:
    settings = get_settings()
    max_age = settings.token_days * 24 * 3600
    try:
        data = _serializer().loads(token, max_age=max_age)
        return data.get("sub") == "allie"
    except (BadSignature, SignatureExpired):
        return False


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if credentials is None or not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )


def token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=get_settings().token_days)
