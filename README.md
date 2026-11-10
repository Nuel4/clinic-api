# Clinic Appointments API

A booking API for a small clinic, built with FastAPI, SQLAlchemy 2 and PostgreSQL. Doctors set weekly opening hours, patients book appointments into them, and the API refuses anything that would double-book a doctor or a patient.

All data in this repository (names, emails, schedules) is made up.

## Features

- Doctors with weekly availability windows, with overlapping windows rejected
- Patients with unique email addresses
- Booking rules, all in one service module (`app/services.py`):
  - no double-booking of a doctor or a patient
  - appointments must fit inside one of the doctor's availability windows
  - start times sit on a 15-minute grid, and lengths are 15 to 120 minutes in 15-minute steps
  - no bookings in the past
- Cancelling keeps the record and frees the time slot
- Free-slot search for a doctor on a given day
- Timezone-aware: opening hours are in the clinic's local time (`CLINIC_TIMEZONE`), and datetimes are stored and returned in UTC
- Alembic migrations, a pytest suite, ruff, Docker Compose and GitHub Actions CI

## Quick start

### With Docker

```bash
docker compose up --build
```

Open http://localhost:8000/docs for the interactive API docs.

### Locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # set DATABASE_URL; leave it unset to use a local SQLite file
alembic upgrade head
uvicorn app.main:app --reload
```

## Example

```bash
# A doctor who works Mondays 09:00-17:00 clinic time
curl -X POST localhost:8000/api/doctors -H 'content-type: application/json' \
  -d '{"full_name": "Dr. Ana Exemplo", "specialty": "general"}'
curl -X POST localhost:8000/api/doctors/1/availability -H 'content-type: application/json' \
  -d '{"weekday": 0, "start_time": "09:00", "end_time": "17:00"}'

# A patient
curl -X POST localhost:8000/api/patients -H 'content-type: application/json' \
  -d '{"full_name": "Test Patient", "email": "patient@example.com"}'

# Free 30-minute slots, then a booking
curl 'localhost:8000/api/doctors/1/free-slots?date=2027-01-11&duration_minutes=30'
curl -X POST localhost:8000/api/appointments -H 'content-type: application/json' \
  -d '{"doctor_id": 1, "patient_id": 1, "starts_at": "2027-01-11T10:00:00Z", "duration_minutes": 30}'
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST, GET | `/api/doctors` | Create or list doctors (`?specialty=`) |
| GET | `/api/doctors/{id}` | One doctor |
| POST, GET | `/api/doctors/{id}/availability` | Add or list weekly opening windows |
| GET | `/api/doctors/{id}/free-slots?date=&duration_minutes=` | Bookable start times on a day |
| POST, GET | `/api/patients` | Create or list patients |
| GET | `/api/patients/{id}` | One patient |
| POST, GET | `/api/appointments` | Book, or list (`?doctor_id=&patient_id=&status=&date=`) |
| GET | `/api/appointments/{id}` | One appointment |
| POST | `/api/appointments/{id}/cancel` | Cancel a future appointment |
| GET | `/health` | Health check |

Errors return `{"detail": "..."}`: 404 when something doesn't exist, 409 for clashes, and 422 for broken rules or invalid input.

## Tests and linting

```bash
pytest
ruff check .
ruff format --check .
```

Tests run on in-memory SQLite with a frozen clock. CI also applies the migrations to PostgreSQL and checks that they match the models.

## Known limitations

- Overlap checks happen in application code, so two simultaneous requests for the same slot could both succeed. The fix (a PostgreSQL exclusion constraint) is on the roadmap.
- There is no authentication yet. Anyone who can reach the API can book or cancel.

## Project layout

```
app/
  main.py         FastAPI app and error handlers
  config.py       Settings (environment variables / .env)
  models.py       SQLAlchemy models
  schemas.py      Pydantic request and response models
  services.py     Booking rules
  routers/        HTTP endpoints
migrations/       Alembic migrations
tests/            pytest suite
```

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
