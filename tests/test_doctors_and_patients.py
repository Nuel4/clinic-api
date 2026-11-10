def test_create_and_list_doctors(client):
    client.post("/api/doctors", json={"full_name": "Dr. One", "specialty": "general"})
    client.post("/api/doctors", json={"full_name": "Dr. Two", "specialty": "dermatology"})

    all_doctors = client.get("/api/doctors").json()
    assert [d["full_name"] for d in all_doctors] == ["Dr. One", "Dr. Two"]

    filtered = client.get("/api/doctors", params={"specialty": "dermatology"}).json()
    assert [d["full_name"] for d in filtered] == ["Dr. Two"]


def test_unknown_doctor_returns_404(client):
    response = client.get("/api/doctors/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor 999 not found"


def test_availability_is_listed(client, doctor):
    windows = client.get(f"/api/doctors/{doctor['id']}/availability").json()
    assert [(w["weekday"], w["start_time"], w["end_time"]) for w in windows] == [
        (0, "09:00:00", "12:00:00"),
        (0, "14:00:00", "17:00:00"),
    ]


def test_overlapping_availability_is_rejected(client, doctor):
    response = client.post(
        f"/api/doctors/{doctor['id']}/availability",
        json={"weekday": 0, "start_time": "11:00", "end_time": "13:00"},
    )
    assert response.status_code == 409


def test_availability_on_another_day_is_allowed(client, doctor):
    response = client.post(
        f"/api/doctors/{doctor['id']}/availability",
        json={"weekday": 1, "start_time": "11:00", "end_time": "13:00"},
    )
    assert response.status_code == 201


def test_availability_end_must_follow_start(client, doctor):
    response = client.post(
        f"/api/doctors/{doctor['id']}/availability",
        json={"weekday": 2, "start_time": "13:00", "end_time": "09:00"},
    )
    assert response.status_code == 422


def test_create_patient_and_reject_duplicate_email(client, patient):
    assert patient["email"] == "patient@example.com"
    duplicate = client.post(
        "/api/patients", json={"full_name": "Someone Else", "email": "patient@example.com"}
    )
    assert duplicate.status_code == 409


def test_invalid_patient_email_is_rejected(client):
    response = client.post("/api/patients", json={"full_name": "X", "email": "not-an-email"})
    assert response.status_code == 422


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
