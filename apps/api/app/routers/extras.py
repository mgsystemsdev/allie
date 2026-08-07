import csv
import io
import json
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import get_settings
from app.db import get_db
from app.models import (
    Contact,
    Elimination,
    EnvReading,
    Feed,
    Handling,
    JournalEntry,
    Maintenance,
    MaintenanceKind,
    Photo,
    PhotoKind,
    Regurgitation,
    ShedCycle,
    Treatment,
    VetVisit,
    Weight,
)
from app.schemas import (
    ContactCreate,
    ContactOut,
    JournalCreate,
    JournalOut,
    LocalStorageImport,
    MaintenanceCreate,
    MaintenanceOut,
    PhotoOut,
    TreatmentCreate,
    TreatmentOut,
)
from app.services.care import get_animal

router = APIRouter(prefix="/api", tags=["extras"], dependencies=[Depends(require_auth)])


def _aid(db: Session) -> int:
    animal = get_animal(db)
    if animal is None:
        raise HTTPException(404, "No animal")
    return animal.id


# --- maintenance ---
@router.get("/maintenance", response_model=list[MaintenanceOut])
def list_maint(db: Session = Depends(get_db)):
    aid = _aid(db)
    rows = list(
        db.scalars(
            select(Maintenance)
            .where(Maintenance.animal_id == aid)
            .order_by(Maintenance.date.desc(), Maintenance.id.desc())
        )
    )
    return [
        MaintenanceOut(id=r.id, animal_id=r.animal_id, date=r.date, kind=r.kind.value, notes=r.notes) for r in rows
    ]


@router.post("/maintenance", response_model=MaintenanceOut)
def create_maint(body: MaintenanceCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    try:
        kind = MaintenanceKind(body.kind)
    except ValueError as exc:
        raise HTTPException(400, "Invalid kind") from exc
    row = Maintenance(animal_id=aid, date=body.date, kind=kind, notes=body.notes or "")
    db.add(row)
    db.commit()
    db.refresh(row)
    return MaintenanceOut(id=row.id, animal_id=row.animal_id, date=row.date, kind=row.kind.value, notes=row.notes)


@router.delete("/maintenance/{item_id}")
def delete_maint(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Maintenance, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- treatments ---
@router.get("/treatments", response_model=list[TreatmentOut])
def list_treatments(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(
        db.scalars(
            select(Treatment).where(Treatment.animal_id == aid).order_by(Treatment.started_at.desc(), Treatment.id.desc())
        )
    )


@router.post("/treatments", response_model=TreatmentOut)
def create_treatment(body: TreatmentCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = Treatment(
        animal_id=aid,
        started_at=body.started_at,
        ended_at=body.ended_at,
        name=body.name,
        reason=body.reason or "",
        notes=body.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/treatments/{item_id}")
def delete_treatment(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Treatment, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- contacts ---
@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(db.scalars(select(Contact).where(Contact.animal_id == aid).order_by(Contact.id.asc())))


@router.post("/contacts", response_model=ContactOut)
def create_contact(body: ContactCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = Contact(
        animal_id=aid,
        label=body.label,
        phone=body.phone or "",
        clinic=body.clinic or "",
        is_emergency=body.is_emergency,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/contacts/{item_id}")
def delete_contact(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Contact, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- journal ---
@router.get("/journal", response_model=list[JournalOut])
def list_journal(db: Session = Depends(get_db)):
    aid = _aid(db)
    return list(
        db.scalars(
            select(JournalEntry)
            .where(JournalEntry.animal_id == aid)
            .order_by(JournalEntry.date.desc(), JournalEntry.id.desc())
        )
    )


@router.post("/journal", response_model=JournalOut)
def create_journal(body: JournalCreate, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = JournalEntry(animal_id=aid, date=body.date, body=body.body)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/journal/{item_id}")
def delete_journal(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(JournalEntry, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- photos ---
def _photo_out(row: Photo) -> PhotoOut:
    return PhotoOut(
        id=row.id,
        animal_id=row.animal_id,
        taken_at=row.taken_at,
        kind=row.kind.value,
        file_path=row.file_path,
        caption=row.caption,
        url=f"/uploads/{Path(row.file_path).name}",
    )


@router.get("/photos", response_model=list[PhotoOut])
def list_photos(db: Session = Depends(get_db)):
    aid = _aid(db)
    rows = list(
        db.scalars(select(Photo).where(Photo.animal_id == aid).order_by(Photo.taken_at.desc(), Photo.id.desc()))
    )
    return [_photo_out(r) for r in rows]


@router.post("/photos", response_model=PhotoOut)
async def upload_photo(
    file: UploadFile = File(...),
    taken_at: date = Form(...),
    kind: str = Form("other"),
    caption: str = Form(""),
    db: Session = Depends(get_db),
):
    aid = _aid(db)
    try:
        photo_kind = PhotoKind(kind)
    except ValueError as exc:
        raise HTTPException(400, "Invalid kind") from exc

    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "photo.jpg").suffix or ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    dest = upload_dir / name
    content = await file.read()
    dest.write_bytes(content)

    row = Photo(
        animal_id=aid,
        taken_at=taken_at,
        kind=photo_kind,
        file_path=str(dest),
        caption=caption or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _photo_out(row)


@router.delete("/photos/{item_id}")
def delete_photo(item_id: int, db: Session = Depends(get_db)):
    aid = _aid(db)
    row = db.get(Photo, item_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Not found")
    path = Path(row.file_path)
    if path.exists():
        path.unlink()
    db.delete(row)
    db.commit()
    return {"ok": True}


# --- export ---
def _serialize_row(obj) -> dict:
    data = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        elif hasattr(val, "value"):
            val = val.value
        data[col.name] = val
    return data


@router.get("/export.json")
def export_json(db: Session = Depends(get_db)):
    aid = _aid(db)
    animal = get_animal(db)
    payload = {
        "animal": _serialize_row(animal),
        "feeds": [_serialize_row(r) for r in db.scalars(select(Feed).where(Feed.animal_id == aid))],
        "weights": [_serialize_row(r) for r in db.scalars(select(Weight).where(Weight.animal_id == aid))],
        "handlings": [_serialize_row(r) for r in db.scalars(select(Handling).where(Handling.animal_id == aid))],
        "shed_cycles": [_serialize_row(r) for r in db.scalars(select(ShedCycle).where(ShedCycle.animal_id == aid))],
        "regurgitations": [
            _serialize_row(r) for r in db.scalars(select(Regurgitation).where(Regurgitation.animal_id == aid))
        ],
        "env_readings": [_serialize_row(r) for r in db.scalars(select(EnvReading).where(EnvReading.animal_id == aid))],
        "eliminations": [_serialize_row(r) for r in db.scalars(select(Elimination).where(Elimination.animal_id == aid))],
        "maintenance": [_serialize_row(r) for r in db.scalars(select(Maintenance).where(Maintenance.animal_id == aid))],
        "treatments": [_serialize_row(r) for r in db.scalars(select(Treatment).where(Treatment.animal_id == aid))],
        "vet_visits": [_serialize_row(r) for r in db.scalars(select(VetVisit).where(VetVisit.animal_id == aid))],
        "contacts": [_serialize_row(r) for r in db.scalars(select(Contact).where(Contact.animal_id == aid))],
        "journal_entries": [
            _serialize_row(r) for r in db.scalars(select(JournalEntry).where(JournalEntry.animal_id == aid))
        ],
        "photos": [_serialize_row(r) for r in db.scalars(select(Photo).where(Photo.animal_id == aid))],
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=allie-export.json"},
    )


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db)):
    aid = _aid(db)
    tables = {
        "feeds": list(db.scalars(select(Feed).where(Feed.animal_id == aid))),
        "weights": list(db.scalars(select(Weight).where(Weight.animal_id == aid))),
        "handlings": list(db.scalars(select(Handling).where(Handling.animal_id == aid))),
        "shed_cycles": list(db.scalars(select(ShedCycle).where(ShedCycle.animal_id == aid))),
        "regurgitations": list(db.scalars(select(Regurgitation).where(Regurgitation.animal_id == aid))),
        "env_readings": list(db.scalars(select(EnvReading).where(EnvReading.animal_id == aid))),
        "eliminations": list(db.scalars(select(Elimination).where(Elimination.animal_id == aid))),
        "maintenance": list(db.scalars(select(Maintenance).where(Maintenance.animal_id == aid))),
        "treatments": list(db.scalars(select(Treatment).where(Treatment.animal_id == aid))),
        "vet_visits": list(db.scalars(select(VetVisit).where(VetVisit.animal_id == aid))),
        "contacts": list(db.scalars(select(Contact).where(Contact.animal_id == aid))),
        "journal_entries": list(db.scalars(select(JournalEntry).where(JournalEntry.animal_id == aid))),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, rows in tables.items():
            text = io.StringIO()
            if not rows:
                text.write("")
            else:
                serialized = [_serialize_row(r) for r in rows]
                writer = csv.DictWriter(text, fieldnames=list(serialized[0].keys()))
                writer.writeheader()
                writer.writerows(serialized)
            zf.writestr(f"{name}.csv", text.getvalue())
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=allie-export.zip"},
    )


# --- localStorage import ---
@router.post("/import/localstorage")
def import_localstorage(body: LocalStorageImport, db: Session = Depends(get_db)):
    aid = _aid(db)
    count = {"feeds": 0, "weights": 0, "sheds": 0, "vet": 0}

    for f in body.feeds:
        accepted = f.get("accept", "yes") == "yes" if "accept" in f else bool(f.get("accepted", True))
        weight = f.get("weight") or f.get("snake_weight_g")
        snake_w = float(weight) if weight not in (None, "") else None
        feed = Feed(
            animal_id=aid,
            date=date.fromisoformat(f["date"]),
            prey_type=f.get("prey") or f.get("prey_type") or "Unknown",
            prey_weight_g=f.get("prey_weight_g"),
            accepted=accepted,
            snake_weight_g=snake_w,
            notes=f.get("notes") or "",
        )
        db.add(feed)
        count["feeds"] += 1
        if snake_w is not None:
            db.add(Weight(animal_id=aid, date=date.fromisoformat(f["date"]), weight_g=snake_w))

    for w in body.weights:
        db.add(
            Weight(
                animal_id=aid,
                date=date.fromisoformat(w["date"]),
                weight_g=float(w["weight"] if "weight" in w else w["weight_g"]),
            )
        )
        count["weights"] += 1

    for s in body.sheds:
        from app.models import ShedStatus

        db.add(
            ShedCycle(
                animal_id=aid,
                status=ShedStatus.shed,
                started_at=date.fromisoformat(s["date"]),
                completed_at=date.fromisoformat(s["date"]),
                quality=s.get("quality"),
                eyes=s.get("eyes"),
                notes="",
            )
        )
        count["sheds"] += 1

    for v in body.vet:
        db.add(
            VetVisit(
                animal_id=aid,
                date=date.fromisoformat(v["date"]),
                reason=v.get("reason") or "Visit",
                notes=v.get("notes") or "",
            )
        )
        count["vet"] += 1

    db.commit()
    return {"ok": True, "imported": count}
