from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])

DB = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: DB):
    if db.scalars(select(Patient).where(Patient.email == payload.email)).first():
        raise services.BookingConflictError("A patient with that email already exists")
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientRead])
def list_patients(db: DB):
    return db.scalars(select(Patient).order_by(Patient.id)).all()


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, db: DB):
    return services.get_patient(db, patient_id)
