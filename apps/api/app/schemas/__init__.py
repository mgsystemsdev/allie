from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    password: str


class AnimalHeroUpdate(BaseModel):
    hero_photo_id: int | None = None


class TokenResponse(BaseModel):
    token: str
    expires_at: datetime


class FeedCreate(BaseModel):
    date: date
    prey_type: str
    prey_weight_g: float | None = None
    accepted: bool = True
    snake_weight_g: float | None = None
    notes: str = ""


class FeedOut(ORMModel):
    id: int
    animal_id: int
    date: date
    prey_type: str
    prey_weight_g: float | None
    accepted: bool
    snake_weight_g: float | None
    notes: str


class WeightCreate(BaseModel):
    date: date
    weight_g: float


class WeightOut(ORMModel):
    id: int
    animal_id: int
    date: date
    weight_g: float


class VetVisitCreate(BaseModel):
    date: date
    reason: str
    notes: str = ""


class VetVisitOut(ORMModel):
    id: int
    animal_id: int
    date: date
    reason: str
    notes: str


class RegurgitationCreate(BaseModel):
    date: date
    related_feed_id: int | None = None
    notes: str = ""
    severity: str = "moderate"


class RegurgitationOut(ORMModel):
    id: int
    animal_id: int
    date: date
    related_feed_id: int | None
    notes: str
    severity: str


class HandlingCreate(BaseModel):
    date: date
    duration_min: int = 15
    temperament: str = "calm"
    notes: str = ""


class HandlingOut(ORMModel):
    id: int
    animal_id: int
    date: date
    duration_min: int
    temperament: str
    notes: str


class ShedCycleCreate(BaseModel):
    status: str
    started_at: date
    completed_at: date | None = None
    quality: str | None = None
    eyes: str | None = None
    notes: str = ""


class ShedCycleUpdate(BaseModel):
    status: str | None = None
    completed_at: date | None = None
    quality: str | None = None
    eyes: str | None = None
    notes: str | None = None


class ShedCycleOut(ORMModel):
    id: int
    animal_id: int
    status: str
    started_at: date
    completed_at: date | None
    quality: str | None
    eyes: str | None
    notes: str


class EnvReadingCreate(BaseModel):
    recorded_at: datetime
    temp_hot_f: float
    temp_cool_f: float
    temp_night_f: float | None = None
    humidity_pct: float
    notes: str = ""


class EnvReadingOut(ORMModel):
    id: int
    animal_id: int
    recorded_at: datetime
    temp_hot_f: float
    temp_cool_f: float
    temp_night_f: float | None
    humidity_pct: float
    notes: str


class EliminationCreate(BaseModel):
    date: date
    kind: str
    related_feed_id: int | None = None
    notes: str = ""


class EliminationOut(ORMModel):
    id: int
    animal_id: int
    date: date
    kind: str
    related_feed_id: int | None
    notes: str


class MaintenanceCreate(BaseModel):
    date: date
    kind: str
    notes: str = ""


class MaintenanceOut(ORMModel):
    id: int
    animal_id: int
    date: date
    kind: str
    notes: str


class TreatmentCreate(BaseModel):
    started_at: date
    ended_at: date | None = None
    name: str
    reason: str = ""
    notes: str = ""


class TreatmentOut(ORMModel):
    id: int
    animal_id: int
    started_at: date
    ended_at: date | None
    name: str
    reason: str
    notes: str


class ContactCreate(BaseModel):
    label: str
    phone: str = ""
    clinic: str = ""
    is_emergency: bool = False


class ContactOut(ORMModel):
    id: int
    animal_id: int
    label: str
    phone: str
    clinic: str
    is_emergency: bool


class JournalCreate(BaseModel):
    date: date
    body: str


class JournalOut(ORMModel):
    id: int
    animal_id: int
    date: date
    body: str


class PhotoOut(ORMModel):
    id: int
    animal_id: int
    taken_at: date
    kind: str
    file_path: str
    caption: str
    url: str = ""


class LocalStorageImport(BaseModel):
    feeds: list[dict] = Field(default_factory=list)
    weights: list[dict] = Field(default_factory=list)
    sheds: list[dict] = Field(default_factory=list)
    vet: list[dict] = Field(default_factory=list)


class AppSettingsUpdate(BaseModel):
    email_enabled: bool | None = None
    reminder_email: str | None = None
    timezone: str | None = None
    digest_enabled: bool | None = None
    digest_time_1: str | None = None
    digest_time_2: str | None = None
    digest_second_enabled: bool | None = None
    feed_ready_days: int | None = None
    handle_clear_hours: int | None = None
    handling_max_gap_days: int | None = None
    maint_water_days: int | None = None
    maint_substrate_days: int | None = None
    maint_deep_clean_days: int | None = None
    feed_interval_mode: str | None = None
    feed_interval_days: int | None = None
    event_handle_cleared: bool | None = None
    event_feed_overdue: bool | None = None
    event_handling_gap: bool | None = None
    event_shed_status: bool | None = None
    event_regurg: bool | None = None
    event_maint_water: bool | None = None
    event_maint_substrate: bool | None = None
    event_maint_deep_clean: bool | None = None
    event_weight_due: bool | None = None
    weight_log_interval_days: int | None = None
    digest_show_feed: bool | None = None
    digest_show_maint: bool | None = None
    digest_show_shed: bool | None = None
    digest_show_handle: bool | None = None
    digest_show_activity: bool | None = None
