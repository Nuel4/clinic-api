from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.routers import appointments, doctors, patients
from app.services import BookingConflictError, BookingRuleError, NotFoundError

app = FastAPI(
    title="Clinic Appointments API",
    version="0.1.0",
    description="Book, list and cancel clinic appointments without double-booking.",
)

app.include_router(doctors.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")


def _error(code: int):
    def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    return handler


app.add_exception_handler(NotFoundError, _error(status.HTTP_404_NOT_FOUND))
app.add_exception_handler(BookingConflictError, _error(status.HTTP_409_CONFLICT))
app.add_exception_handler(BookingRuleError, _error(status.HTTP_422_UNPROCESSABLE_CONTENT))


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
