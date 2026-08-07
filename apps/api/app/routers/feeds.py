from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models import Feed, Weight
from app.schemas import FeedCreate, FeedOut, WeightCreate, WeightOut
from app.services.care import get_animal

router = APIRouter(prefix="/api", tags=["feeds"], dependencies=[Depends(require_auth)])


def _animal_id(db: Session) -> int:
    animal = get_animal(db)
    if animal is None:
        raise HTTPException(404, "No animal")
    return animal.id


@router.get("/feeds", response_model=list[FeedOut])
def list_feeds(db: Session = Depends(get_db)):
    aid = _animal_id(db)
    rows = db.scalars(select(Feed).where(Feed.animal_id == aid).order_by(Feed.date.desc(), Feed.id.desc()))
    return list(rows)


@router.post("/feeds", response_model=FeedOut)
def create_feed(body: FeedCreate, db: Session = Depends(get_db)):
    aid = _animal_id(db)
    feed = Feed(
        animal_id=aid,
        date=body.date,
        prey_type=body.prey_type,
        prey_weight_g=body.prey_weight_g,
        accepted=body.accepted,
        snake_weight_g=body.snake_weight_g,
        notes=body.notes or "",
    )
    db.add(feed)
    if body.snake_weight_g is not None:
        db.add(Weight(animal_id=aid, date=body.date, weight_g=body.snake_weight_g))
    db.commit()
    db.refresh(feed)
    return feed


@router.delete("/feeds/{feed_id}")
def delete_feed(feed_id: int, db: Session = Depends(get_db)):
    aid = _animal_id(db)
    feed = db.get(Feed, feed_id)
    if feed is None or feed.animal_id != aid:
        raise HTTPException(404, "Feed not found")
    db.delete(feed)
    db.commit()
    return {"ok": True}


@router.get("/weights", response_model=list[WeightOut])
def list_weights(db: Session = Depends(get_db)):
    aid = _animal_id(db)
    rows = db.scalars(select(Weight).where(Weight.animal_id == aid).order_by(Weight.date.asc(), Weight.id.asc()))
    return list(rows)


@router.post("/weights", response_model=WeightOut)
def create_weight(body: WeightCreate, db: Session = Depends(get_db)):
    aid = _animal_id(db)
    row = Weight(animal_id=aid, date=body.date, weight_g=body.weight_g)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/weights/{weight_id}")
def delete_weight(weight_id: int, db: Session = Depends(get_db)):
    aid = _animal_id(db)
    row = db.get(Weight, weight_id)
    if row is None or row.animal_id != aid:
        raise HTTPException(404, "Weight not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
