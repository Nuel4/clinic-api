from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./clinic.db"
    # Opening hours are entered and checked in this timezone; datetimes are stored in UTC.
    clinic_timezone: str = "Europe/Lisbon"
    # Appointments start on this grid and last a multiple of it.
    slot_minutes: int = 15
    min_appointment_minutes: int = 15
    max_appointment_minutes: int = 120

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.clinic_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
