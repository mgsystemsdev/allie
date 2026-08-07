import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Temperament(str, enum.Enum):
    calm = "calm"
    nippy = "nippy"
    musk = "musk"


class ShedStatus(str, enum.Enum):
    clear = "clear"
    blue = "blue"
    opaque = "opaque"
    shed = "shed"


class EliminationKind(str, enum.Enum):
    feces = "feces"
    urates = "urates"
    both = "both"


class MaintenanceKind(str, enum.Enum):
    water = "water"
    substrate = "substrate"
    deep_clean = "deep_clean"


class PhotoKind(str, enum.Enum):
    growth = "growth"
    shed = "shed"
    body_condition = "body_condition"
    other = "other"


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(200), nullable=False)
    common_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False, default="female")
    owner: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active & Healthy")


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    prey_type: Mapped[str] = mapped_column(String(100), nullable=False)
    prey_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    snake_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Regurgitation(Base):
    __tablename__ = "regurgitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    related_feed_id: Mapped[int | None] = mapped_column(ForeignKey("feeds.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="moderate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Weight(Base):
    __tablename__ = "weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Handling(Base):
    __tablename__ = "handlings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    temperament: Mapped[Temperament] = mapped_column(
        Enum(Temperament, name="temperament"), nullable=False, default=Temperament.calm
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShedCycle(Base):
    __tablename__ = "shed_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    status: Mapped[ShedStatus] = mapped_column(
        Enum(ShedStatus, name="shed_status"), nullable=False, default=ShedStatus.clear
    )
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eyes: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnvReading(Base):
    __tablename__ = "env_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temp_hot_f: Mapped[float] = mapped_column(Float, nullable=False)
    temp_cool_f: Mapped[float] = mapped_column(Float, nullable=False)
    temp_night_f: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Elimination(Base):
    __tablename__ = "eliminations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[EliminationKind] = mapped_column(
        Enum(EliminationKind, name="elimination_kind"), nullable=False
    )
    related_feed_id: Mapped[int | None] = mapped_column(ForeignKey("feeds.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Maintenance(Base):
    __tablename__ = "maintenance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[MaintenanceKind] = mapped_column(
        Enum(MaintenanceKind, name="maintenance_kind"), nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    taken_at: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[PhotoKind] = mapped_column(
        Enum(PhotoKind, name="photo_kind"), nullable=False, default=PhotoKind.other
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    clinic: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VetVisit(Base):
    __tablename__ = "vet_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reminder_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Chicago")

    digest_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_time_1: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00")
    digest_time_2: Mapped[str] = mapped_column(String(5), nullable=False, default="20:00")
    digest_second_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    feed_ready_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    handle_clear_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    handling_max_gap_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    maint_water_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    maint_substrate_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    maint_deep_clean_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)

    feed_interval_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    feed_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    event_handle_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_feed_overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_handling_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_shed_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_regurg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_maint_water: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_maint_substrate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_maint_deep_clean: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_weight_due: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    weight_log_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    digest_show_feed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_show_maint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_show_shed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_show_handle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_show_activity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EmailSendLog(Base):
    __tablename__ = "email_send_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
