"""Booking rules. All checks live here so the API layer stays thin."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Appointment, AppointmentStatus, Availability, Doctor, Patient


class NotFoundError(Exception):
    pass


class BookingRuleError(Exception):
    """The request breaks a booking rule (wrong length, outside opening hours, in the past...)."""


class BookingConflictError(Exception):
    """The requested time clashes with an existing appointment."""


def get_doctor(db: Session, doctor_id: int) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise NotFoundError(f"Doctor {doctor_id} not found")
    return doctor


def get_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found")
    return patient


def get_appointment(db: Session, appointment_id: int) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    return appointment


def _overlapping(db: Session, starts_at: datetime, ends_at: datetime, **owner) -> Appointment | None:
    """Return a booked appointment for the given doctor or patient that overlaps [starts_at, ends_at)."""
    ((column, value),) = owner.items()
    stmt = (
        select(Appointment)
        .where(getattr(Appointment, column) == value)
        .where(Appointment.status == AppointmentStatus.BOOKED)
        .where(Appointment.starts_at < ends_at)
        .where(Appointment.ends_at > starts_at)
        .limit(1)
    )
    return db.scalars(stmt).first()


def _fits_availability(doctor: Doctor, starts_at: datetime, ends_at: datetime, settings: Settings) -> bool:
    local_start = starts_at.astimezone(settings.tz)
    for window in doctor.availability:
        if window.weekday != local_start.weekday():
            continue
        window_start = datetime.combine(local_start.date(), window.start_time, settings.tz)
        window_end = datetime.combine(local_start.date(), window.end_time, settings.tz)
        if window_start <= starts_at and ends_at <= window_end:
            return True
    return False


def add_availability(db: Session, doctor_id: int, *, weekday: int, start_time, end_time) -> Availability:
    doctor = get_doctor(db, doctor_id)
    for window in doctor.availability:
        if window.weekday == weekday and window.start_time < end_time and window.end_time > start_time:
            raise BookingConflictError(
                f"Overlaps an existing window ({window.start_time:%H:%M}-{window.end_time:%H:%M})"
            )
    window = Availability(weekday=weekday, start_time=start_time, end_time=end_time)
    doctor.availability.append(window)
    db.commit()
    db.refresh(window)
    return window


def book_appointment(
    db: Session,
    *,
    doctor_id: int,
    patient_id: int,
    starts_at: datetime,
    duration_minutes: int,
    reason: str | None,
    now: datetime,
    settings: Settings,
) -> Appointment:
    step = settings.slot_minutes
    if not settings.min_appointment_minutes <= duration_minutes <= settings.max_appointment_minutes:
        raise BookingRuleError(
            f"Duration must be between {settings.min_appointment_minutes} "
            f"and {settings.max_appointment_minutes} minutes"
        )
    if duration_minutes % step:
        raise BookingRuleError(f"Duration must be a multiple of {step} minutes")

    local_start = starts_at.astimezone(settings.tz)
    if local_start.minute % step or local_start.second or local_start.microsecond:
        raise BookingRuleError(f"Appointments must start on a {step}-minute boundary")
    if starts_at <= now:
        raise BookingRuleError("Appointments cannot be booked in the past")

    doctor = get_doctor(db, doctor_id)
    if not doctor.is_active:
        raise BookingRuleError(f"Doctor {doctor_id} is not taking appointments")
    get_patient(db, patient_id)

    ends_at = starts_at + timedelta(minutes=duration_minutes)
    if not _fits_availability(doctor, starts_at, ends_at, settings):
        raise BookingRuleError("The doctor is not available at that time")
    if _overlapping(db, starts_at, ends_at, doctor_id=doctor_id):
        raise BookingConflictError("The doctor already has an appointment at that time")
    if _overlapping(db, starts_at, ends_at, patient_id=patient_id):
        raise BookingConflictError("The patient already has an appointment at that time")

    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, appointment_id: int, *, now: datetime) -> Appointment:
    appointment = get_appointment(db, appointment_id)
    if appointment.status != AppointmentStatus.BOOKED:
        raise BookingRuleError(f"Only booked appointments can be cancelled (status is {appointment.status})")
    if appointment.starts_at <= now:
        raise BookingRuleError("Appointments that have already started cannot be cancelled")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = now
    db.commit()
    db.refresh(appointment)
    return appointment


def free_slots(
    db: Session,
    doctor_id: int,
    on_date: date,
    duration_minutes: int,
    *,
    now: datetime,
    settings: Settings,
) -> list[tuple[datetime, datetime]]:
    """Every start time on `on_date` (clinic local date) where a booking of this length would succeed."""
    doctor = get_doctor(db, doctor_id)
    if not doctor.is_active:
        return []

    step = timedelta(minutes=settings.slot_minutes)
    length = timedelta(minutes=duration_minutes)
    day_start = datetime.combine(on_date, datetime.min.time(), settings.tz)
    day_end = day_start + timedelta(days=1)

    booked = db.scalars(
        select(Appointment)
        .where(Appointment.doctor_id == doctor_id)
        .where(Appointment.status == AppointmentStatus.BOOKED)
        .where(Appointment.starts_at < day_end)
        .where(Appointment.ends_at > day_start)
    ).all()

    windows: list[Availability] = [w for w in doctor.availability if w.weekday == on_date.weekday()]
    slots = []
    for window in sorted(windows, key=lambda w: w.start_time):
        cursor = datetime.combine(on_date, window.start_time, settings.tz)
        window_end = datetime.combine(on_date, window.end_time, settings.tz)
        while cursor + length <= window_end:
            end = cursor + length
            clash = any(a.starts_at < end and a.ends_at > cursor for a in booked)
            if cursor > now and not clash:
                slots.append((cursor.astimezone(UTC), end.astimezone(UTC)))
            cursor += step
    return slots
