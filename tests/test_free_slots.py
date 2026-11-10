from tests.conftest import MONDAY, NEXT_MONDAY, TUESDAY


def slots(client, doctor, day, duration=30):
    response = client.get(
        f"/api/doctors/{doctor['id']}/free-slots", params={"date": day, "duration_minutes": duration}
    )
    assert response.status_code == 200
    return [s["starts_at"][11:16] for s in response.json()]  # UTC HH:MM


def test_full_day_of_slots(client, doctor):
    result = slots(client, doctor, NEXT_MONDAY)
    # 09:00-11:30 and 14:00-16:30 local every 15 minutes = 11 + 11 slots.
    assert len(result) == 22
    assert result[0] == "08:00"  # 09:00 Lisbon
    assert result[-1] == "15:30"  # 16:30 Lisbon


def test_booked_time_is_excluded(client, doctor, book):
    book(starts_at=f"{NEXT_MONDAY}T10:00:00+01:00")
    result = slots(client, doctor, NEXT_MONDAY)
    # 09:45, 10:00 and 10:15 local all overlap 10:00-10:30.
    assert {"08:45", "09:00", "09:15"}.isdisjoint(result)
    assert {"08:30", "09:30"} <= set(result)


def test_cancelled_appointments_do_not_block(client, doctor, book):
    appointment = book(starts_at=f"{NEXT_MONDAY}T10:00:00+01:00").json()
    client.post(f"/api/appointments/{appointment['id']}/cancel")
    assert len(slots(client, doctor, NEXT_MONDAY)) == 22


def test_longer_appointments_have_fewer_slots(client, doctor):
    assert len(slots(client, doctor, NEXT_MONDAY, duration=120)) == 2 * 5


def test_no_slots_on_days_off(client, doctor):
    assert slots(client, doctor, TUESDAY) == []


def test_slots_in_the_past_are_hidden(client, doctor):
    # Now is 08:00 Lisbon on MONDAY, before opening, so the whole day is still free.
    assert len(slots(client, doctor, MONDAY)) == 22
