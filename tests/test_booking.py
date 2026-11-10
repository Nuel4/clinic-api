import pytest

from tests.conftest import MONDAY, NEXT_MONDAY, TUESDAY


def test_book_appointment(book):
    response = book(reason="Check-up")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "booked"
    # 09:00 Lisbon summer time is 08:00 UTC.
    assert body["starts_at"].startswith(f"{MONDAY}T08:00:00")
    assert body["ends_at"].startswith(f"{MONDAY}T08:30:00")
    assert body["reason"] == "Check-up"


def test_utc_input_is_accepted(book):
    assert book(starts_at=f"{MONDAY}T08:00:00Z").status_code == 201


def test_naive_datetime_is_rejected(book):
    assert book(starts_at=f"{MONDAY}T09:00:00").status_code == 422


def test_opening_hours_use_clinic_timezone(book):
    # 07:00 UTC is 08:00 in Lisbon, an hour before the doctor starts.
    response = book(starts_at=f"{NEXT_MONDAY}T07:00:00Z")
    assert response.status_code == 422
    assert response.json()["detail"] == "The doctor is not available at that time"


@pytest.mark.parametrize(
    "starts_at",
    [
        f"{MONDAY}T08:00:00+01:00",  # before opening
        f"{MONDAY}T11:45:00+01:00",  # 30 minutes would run past 12:00
        f"{MONDAY}T12:00:00+01:00",  # lunch gap
        f"{MONDAY}T16:45:00+01:00",  # runs past closing
        f"{TUESDAY}T10:00:00+01:00",  # doctor does not work Tuesdays
    ],
)
def test_outside_availability_is_rejected(book, starts_at):
    assert book(starts_at=starts_at).status_code == 422


def test_cannot_span_two_windows(book):
    response = book(starts_at=f"{MONDAY}T11:30:00+01:00", duration_minutes=180)
    assert response.status_code == 422


def test_booking_at_window_edges_is_allowed(book):
    assert book(starts_at=f"{MONDAY}T11:30:00+01:00").status_code == 201
    assert book(starts_at=f"{MONDAY}T14:00:00+01:00").status_code == 201


def test_past_booking_is_rejected(client, doctor, patient):
    # Now is 08:00 Lisbon on MONDAY; a doctor open from 06:00 makes the hours check pass.
    client.post(
        f"/api/doctors/{doctor['id']}/availability",
        json={"weekday": 0, "start_time": "06:00", "end_time": "08:30"},
    )
    response = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor["id"],
            "patient_id": patient["id"],
            "starts_at": f"{MONDAY}T07:30:00+01:00",
            "duration_minutes": 30,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Appointments cannot be booked in the past"


@pytest.mark.parametrize("duration", [10, 20, 135, 240])
def test_invalid_duration_is_rejected(book, duration):
    assert book(duration_minutes=duration).status_code == 422


def test_start_must_be_on_the_slot_grid(book):
    assert book(starts_at=f"{MONDAY}T09:10:00+01:00").status_code == 422


def test_doctor_cannot_be_double_booked(client, book):
    assert book().status_code == 201
    other = client.post("/api/patients", json={"full_name": "Other", "email": "other@example.com"}).json()

    response = book(patient_id=other["id"], starts_at=f"{MONDAY}T09:15:00+01:00")
    assert response.status_code == 409
    assert response.json()["detail"] == "The doctor already has an appointment at that time"


def test_back_to_back_appointments_are_allowed(client, book):
    other = client.post("/api/patients", json={"full_name": "Other", "email": "other@example.com"}).json()
    assert book().status_code == 201
    assert book(patient_id=other["id"], starts_at=f"{MONDAY}T09:30:00+01:00").status_code == 201


def test_patient_cannot_be_double_booked_across_doctors(client, book, patient):
    second = client.post("/api/doctors", json={"full_name": "Dr. Second", "specialty": "general"}).json()
    client.post(
        f"/api/doctors/{second['id']}/availability",
        json={"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
    )
    assert book().status_code == 201

    response = book(doctor_id=second["id"], starts_at=f"{MONDAY}T09:15:00+01:00")
    assert response.status_code == 409
    assert response.json()["detail"] == "The patient already has an appointment at that time"


def test_unknown_doctor_or_patient(book):
    assert book(doctor_id=999).status_code == 404
    assert book(patient_id=999).status_code == 404


def test_cancel_frees_the_slot(client, book):
    appointment = book().json()

    cancelled = client.post(f"/api/appointments/{appointment['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None

    assert book().status_code == 201


def test_cannot_cancel_twice(client, book):
    appointment = book().json()
    client.post(f"/api/appointments/{appointment['id']}/cancel")
    assert client.post(f"/api/appointments/{appointment['id']}/cancel").status_code == 422


def test_list_appointments_filters(client, book):
    first = book().json()
    book(starts_at=f"{NEXT_MONDAY}T10:00:00+01:00")
    client.post(f"/api/appointments/{first['id']}/cancel")

    on_monday = client.get("/api/appointments", params={"date": MONDAY}).json()
    assert [a["id"] for a in on_monday] == [first["id"]]

    booked = client.get("/api/appointments", params={"status": "booked"}).json()
    assert len(booked) == 1
    assert booked[0]["starts_at"].startswith(f"{NEXT_MONDAY}T09:00:00")
