from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models import (
    Elimination,
    EliminationKind,
    EnvReading,
    Handling,
    Regurgitation,
    ShedCycle,
    ShedStatus,
    Temperament,
    VetVisit,
)
from app.schemas import (
    EliminationCreate,
    EliminationOut,
    EnvReadingCreate,
    EnvReadingOut,
    HandlingCreate,
    HandlingOut,
    RegurgitationCreate,
    RegurgitationOut,
    ShedCycleCreate,
    ShedCycleOut,
    ShedCycleUpdate,
    VetVisitCreate,
    VetVisitOut,
)
from app.services.care import get_animal

router = APIRouter(prefix="/api", tags=["care"], dependencies=[Depends(require_auth)])


def _aid(db: Session) -> int:
    animal = get_animal(db)
    if animal is None:
        raise HTTPException(404, "No animal")
    return animal.id


# --- regurgitations ---
@router.get("/regurgitations", response_model=list[RegurgitationOut])
def list_regurg(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(
        db.scalars(
            select(Regurgitation)
            .where(Regurgitation.animal_id == aid)
            .order_by(Regurgitation.date.desc(), Regurgitation.id.desc())
        )
    )


@router.post("/regurgitations", response_model=RegurgitationOut)
def create_regurg(body: RegurgitationCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = Regurgitation(
        animal_id=aid,
        date=body.date,
        related_feed_id=body.related_feed_id,
        notes=body.notes or "",
        severity=body.severity,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        from app.services.email_svc import notify_regurg

        notify_regurg(db, row.id, row.notes)
    except Exception:
        pass
    return row


@router.delete("/regurgitations/{item_id}")
def delete_regurg(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Regurgitation, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- handlings ---
@router.get("/handlings", response_model=list[HandlingOut])
def list_handlings(db: Session = Depends(get_db)):
    aid = _aid(db)
    rows = list(
        db.scalars(
            select(Handling).where(Handling.animal_id == aid).order_by(Handling.date.desc(), Handling.id.desc())
        )
    )
    return [
        HandlingOut(
            id=r.id,
            animal_id=r.animal_id,
            date=r.date,
            duration_min=r.duration_min,
            temperament=r.temperament.value,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post("/handlings", response_model=HandlingOut)
def create_handling(body: HandlingCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    try:
        temp = Temperament(body.temperament)
    except ValueError as exc:
        raise HTTPException(400, "Invalid temperament") from exc
    row = Handling(
        animal_id=aid,
        date=body.date,
        duration_min=body.duration_min,
        temperament=temp,
        notes=body.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return HandlingOut(
        id=row.id,
        animal_id=row.animal_id,
        date=row.date,
        duration_min=row.duration_min,
        temperament=row.temperament.value,
        notes=row.notes,
    )


@router.delete("/handlings/{item_id}")
def delete_handling(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Handling, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- shed cycles ---
@router.get("/shed-cycles", response_model=list[ShedCycleOut])
def list_sheds(db: Session = Depends(get_db)):
    aid = _aid(db)
    rows = list(
        db.scalars(
            select(ShedCycle).where(ShedCycle.animal_id == aid).order_by(ShedCycle.started_at.desc(), ShedCycle.id.desc())
        )
    )
    return [
        ShedCycleOut(
            id=r.id,
            animal_id=r.animal_id,
            status=r.status.value,
            started_at=r.started_at,
            completed_at=r.completed_at,
            quality=r.quality,
            eyes=r.eyes,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post("/shed-cycles", response_model=ShedCycleOut)
def create_shed(body: ShedCycleCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    try:
        status = ShedStatus(body.status)
    except ValueError as exc:
        raise HTTPException(400, "Invalid shed status") from exc
    row = ShedCycle(
        animal_id=aid,
        status=status,
        started_at=body.started_at,
        completed_at=body.completed_at,
        quality=body.quality,
        eyes=body.eyes,
        notes=body.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        from app.services.email_svc import notify_shed_status

        notify_shed_status(db, row.status.value, row.id)
    except Exception:
        pass
    return ShedCycleOut(
        id=row.id,
        animal_id=row.animal_id,
        status=row.status.value,
        started_at=row.started_at,
        completed_at=row.completed_at,
        quality=row.quality,
        eyes=row.eyes,
        notes=row.notes,
    )


@router.patch("/shed-cycles/{item_id}", response_model=ShedCycleOut)
def update_shed(item_id: int, body: ShedCycleUpdate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(ShedCycle, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    if body.status is not None:
        try:
            row.status = ShedStatus(body.status)
        except ValueError as exc:
            raise HTTPException(400, "Invalid shed status") from exc
    if body.completed_at is not None:
        row.completed_at = body.completed_at
    if body.quality is not None:
        row.quality = body.quality
    if body.eyes is not None:
        row.eyes = body.eyes
    if body.notes is not None:
        row.notes = body.notes
    db.commit()
    db.refresh(row)
    try:
        from app.services.email_svc import notify_shed_status

        notify_shed_status(db, row.status.value, row.id)
    except Exception:
        pass
    return ShedCycleOut(
        id=row.id,
        animal_id=row.animal_id,
        status=row.status.value,
        started_at=row.started_at,
        completed_at=row.completed_at,
        quality=row.quality,
        eyes=row.eyes,
        notes=row.notes,
    )


@router.delete("/shed-cycles/{item_id}")
def delete_shed(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(ShedCycle, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- env readings ---
@router.get("/env-readings", response_model=list[EnvReadingOut])
def list_env(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(
        db.scalars(
            select(EnvReading)
            .where(EnvReading.animal_id == aid)
            .order_by(EnvReading.recorded_at.desc(), EnvReading.id.desc())
        )
    )


@router.post("/env-readings", response_model=EnvReadingOut)
def create_env(body: EnvReadingCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = EnvReading(
        animal_id=aid,
        recorded_at=body.recorded_at,
        temp_hot_f=body.temp_hot_f,
        temp_cool_f=body.temp_cool_f,
        temp_night_f=body.temp_night_f,
        humidity_pct=body.humidity_pct,
        notes=body.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/env-readings/{item_id}")
def delete_env(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(EnvReading, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- eliminations ---
@router.get("/eliminations", response_model=list[EliminationOut])
def list_elim(db: Session = Depends(get_db)):
    aid = _aid(db)
    rows = list(
        db.scalars(
            select(Elimination)
            .where(Elimination.animal_id == aid)
            .order_by(Elimination.date.desc(), Elimination.id.desc())
        )
    )
    return [
        EliminationOut(
            id=r.id,
            animal_id=r.animal_id,
            date=r.date,
            kind=r.kind.value,
            related_feed_id=r.related_feed_id,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post("/eliminations", response_model=EliminationOut)
def create_elim(body: EliminationCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    try:
        kind = EliminationKind(body.kind)
    except ValueError as exc:
        raise HTTPException(400, "Invalid kind") from exc
    row = Elimination(
        animal_id=aid,
        date=body.date,
        kind=kind,
        related_feed_id=body.related_feed_id,
        notes=body.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return EliminationOut(
        id=row.id,
        animal_id=row.animal_id,
        date=row.date,
        kind=row.kind.value,
        related_feed_id=row.related_feed_id,
        notes=row.notes,
    )


@router.delete("/eliminations/{item_id}")
def delete_elim(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Elimination, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- vet visits ---
@router.get("/vet-visits", response_model=list[VetVisitOut])
def list_vet(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(
        db.scalars(select(VetVisit).where(VetVisit.animal_id == aid).order_by(VetVisit.date.desc(), VetVisit.id.desc()))
    )


@router.post("/vet-visits", response_model=VetVisitOut)
def create_vet(body: VetVisitCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = VetVisit(animal_id=aid, date=body.date, reason=body.reason, notes=body.notes or "")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/vet-visits/{item_id}")
def delete_vet(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(VetVisit, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
