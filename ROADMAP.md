# Roadmap

Items are ticked only when they are merged and tested. All sample data stays made up.

## v0.1: core booking (done)
- [x] Doctors, weekly availability and patients
- [x] Book and cancel appointments with no double-booking of doctor or patient
- [x] Opening hours in clinic local time, storage in UTC
- [x] Free-slot search
- [x] Alembic migrations, tests, CI and Docker

## v0.2: correctness under load
- [ ] Prevent double-booking at the database level (PostgreSQL exclusion constraint), with a concurrency test
- [ ] Pagination for list endpoints
- [ ] Consistent error format with machine-readable error codes

## v0.3: schedule changes
- [ ] Reschedule an appointment in one request, keeping its history
- [ ] Doctor time off and clinic holidays that block booking
- [ ] Removing or shrinking an availability window when future appointments fall inside it
- [ ] Deactivate a doctor and handle their future appointments

## v0.4: appointment lifecycle
- [ ] Mark appointments as completed or no-show
- [ ] Cancellation cut-off (for example, no cancelling within 24 hours)
- [ ] Buffer time between appointments, configurable per doctor

## v0.5: access control
- [ ] Authentication with roles: receptionist, doctor, admin
- [ ] Doctors see only their own schedule
- [ ] Audit log of who booked, changed or cancelled what

## v0.6: notifications
- [ ] Email reminders before an appointment, sent by a background worker
- [ ] iCalendar (.ics) export of a doctor's schedule

## Ideas, not committed to
- Waiting list that offers freed slots automatically
- Recurring appointments (for example, weekly physiotherapy)
