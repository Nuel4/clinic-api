from datetime import date, datetime, time

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import AppointmentStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Doctors and availability


class DoctorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    specialty: str = Field(min_length=1, max_length=100)


class DoctorRead(ORMModel):
    id: int
    full_name: str
    specialty: str
    is_active: bool


class AvailabilityCreate(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = Monday, 6 = Sunday")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_order(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class AvailabilityRead(ORMModel):
    id: int
    weekday: int
    start_time: time
    end_time: time


class FreeSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime


# Patients


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)


class PatientRead(ORMModel):
    id: int
    full_name: str
    email: str
    phone: str | None


# Appointments


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    starts_at: AwareDatetime
    duration_minutes: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)


class AppointmentRead(ORMModel):
    id: int
    doctor_id: int
    patient_id: int
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    reason: str | None
    cancelled_at: datetime | None


class AppointmentFilters(BaseModel):
    doctor_id: int | None = None
    patient_id: int | None = None
    on_date: date | None = None
    status: AppointmentStatus | None = None
