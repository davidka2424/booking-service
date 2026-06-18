import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.booking import BookingStatus, ServiceType


class BookingCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Customer full name",
        examples=["Ivan Petrov"],
    )
    scheduled_at: datetime = Field(
        ...,
        description="Desired appointment datetime (ISO 8601 with timezone)",
        examples=["2025-03-01T10:00:00+03:00"],
    )
    service_type: ServiceType = Field(
        ...,
        description="Type of service requested",
        examples=[ServiceType.CONSULTATION],
    )

    @field_validator("scheduled_at")
    @classmethod
    def scheduled_at_must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(tz=UTC)
        if v.tzinfo is None:
            raise ValueError("scheduled_at must include timezone info")
        if v <= now:
            raise ValueError("scheduled_at must be in the future")
        return v


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    service_type: ServiceType
    scheduled_at: datetime
    status: BookingStatus
    notification_sent: bool
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    size: int
    pages: int


class BookingFilters(BaseModel):
    status: BookingStatus | None = Field(None, description="Filter by booking status")
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")