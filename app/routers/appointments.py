from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.clock import get_now
from app.config import Settings, get_settings
from app.database import get_db
from app.models import Appointment, AppointmentStatus
from app.schemas import AppointmentCreate, AppointmentRead

router = APIRouter(prefix="/appointments", tags=["appointments"])

DB = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def book(payload: AppointmentCreate, db: DB, now: Now, settings: AppSettings):
    return services.book_appointment(db, **payload.model_dump(), now=now, settings=settings)


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: DB,
    settings: AppSettings,
    doctor_id: int | None = None,
    patient_id: int | None = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
    on_date: Annotated[date | None, Query(alias="date", description="Clinic local date")] = None,
):
    stmt = select(Appointment).order_by(Appointment.starts_at)
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter)
    if on_date is not None:
        day_start = datetime.combine(on_date, datetime.min.time(), settings.tz)
        stmt = stmt.where(Appointment.starts_at >= day_start).where(
            Appointment.starts_at < day_start + timedelta(days=1)
        )
    return db.scalars(stmt).all()


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: DB):
    return services.get_appointment(db, appointment_id)


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel(appointment_id: int, db: DB, now: Now):
    return services.cancel_appointment(db, appointment_id, now=now)
