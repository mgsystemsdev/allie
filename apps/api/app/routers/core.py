from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import create_token, require_auth, token_expires_at
from app.config import get_settings
from app.db import get_db
from app.schemas import AnimalHeroUpdate, LoginRequest, TokenResponse
from app.services.care import build_overview, calc_age, get_animal, set_animal_hero
from app.services.feeding_rules import feeding_config, recommend_feeding

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


@router.patch("/animal")
def patch_animal(
    body: AnimalHeroUpdate,
    _: None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    animal = get_animal(db)
    if animal is None:
        raise HTTPException(status_code=404, detail="No animal")
    try:
        set_animal_hero(db, animal, body.hero_photo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_overview(db)


@router.get("/feeding/config")
def get_feeding_config(_: None = Depends(require_auth)) -> dict:
    return feeding_config()


@router.get("/feeding/recommend")
def get_feeding_recommend(
    prey: str | None = Query(default=None),
    _: None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    animal = get_animal(db)
    if animal is None:
        raise HTTPException(status_code=404, detail="No animal")
    age = calc_age(animal.dob)
    return recommend_feeding(age["months"], prey)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
