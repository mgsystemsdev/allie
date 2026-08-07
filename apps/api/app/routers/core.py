from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_token, require_auth, token_expires_at
from app.config import get_settings
from app.db import get_db
from app.schemas import LoginRequest, TokenResponse
from app.services.care import build_overview, get_animal

router = APIRouter(prefix="/api", tags=["core"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    if body.password != get_settings().app_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    return TokenResponse(token=create_token(), expires_at=token_expires_at())


@router.get("/animal")
def animal_overview(_: None = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        return build_overview(db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
