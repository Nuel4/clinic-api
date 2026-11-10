from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.clock import get_now
from app.config import Settings, get_settings
from app.database import get_db
from app.models import Doctor
from app.schemas import AvailabilityCreate, AvailabilityRead, DoctorCreate, DoctorRead, FreeSlot

router = APIRouter(prefix="/doctors", tags=["doctors"])

DB = Annotated[Session, Depends(get_db)]


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: DB):
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("", response_model=list[DoctorRead])
def list_doctors(db: DB, specialty: str | None = None):
    stmt = select(Doctor).order_by(Doctor.id)
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    return db.scalars(stmt).all()


@router.get("/{doctor_id}", response_model=DoctorRead)
def get_doctor(doctor_id: int, db: DB):
    return services.get_doctor(db, doctor_id)


@router.post(
    "/{doctor_id}/availability", response_model=AvailabilityRead, status_code=status.HTTP_201_CREATED
)
def add_availability(doctor_id: int, payload: AvailabilityCreate, db: DB):
    return services.add_availability(db, doctor_id, **payload.model_dump())


@router.get("/{doctor_id}/availability", response_model=list[AvailabilityRead])
def list_availability(doctor_id: int, db: DB):
    return services.get_doctor(db, doctor_id).availability


@router.get("/{doctor_id}/free-slots", response_model=list[FreeSlot])
def free_slots(
    doctor_id: int,
    db: DB,
    on_date: Annotated[date, Query(alias="date")],
    settings: Annotated[Settings, Depends(get_settings)],
    now: Annotated[datetime, Depends(get_now)],
    duration_minutes: Annotated[int, Query(gt=0)] = 30,
):
    slots = services.free_slots(db, doctor_id, on_date, duration_minutes, now=now, settings=settings)
    return [FreeSlot(starts_at=start, ends_at=end) for start, end in slots]
