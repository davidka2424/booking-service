import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base  # type: ignore[misc]

class BookingStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ServiceType(enum.StrEnum):
    CONSULTATION = "consultation"
    REPAIR = "repair"
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"


class Booking(Base):
    __tablename__ = "bookings"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(
        Enum(
            ServiceType,
            name="service_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        unique=True,
        comment="TaskIQ task ID for idempotency",
    )
    notification_sent: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} status={self.status} service={self.service_type}>"
        )
