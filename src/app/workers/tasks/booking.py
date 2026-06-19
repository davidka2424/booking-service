import random
import uuid

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.db.models.booking import BookingStatus
from app.db.session import get_session_factory
from app.repositories.booking import BookingRepository
from app.workers.broker import broker

logger = get_logger(__name__)


async def _mock_external_notification(booking_id: uuid.UUID, name: str) -> None:
    """Simulates sending a notification via external service."""
    log = logger.bind(booking_id=str(booking_id), customer=name)
    log.info("mock_notification.sending")
    log.info(
        "mock_notification.sent",
        channel="email",
        template="booking_confirmed",
    )


@broker.task( #type: ignore[misk]
    task_name="confirm_booking",
    retry_on_error=True,
    max_retries=3,
)
async def confirm_booking(booking_id: str) -> dict[str, str]:
    """
    Confirms a booking asynchronously.

    Idempotency guarantee:
    - Task is keyed by booking_id (UUID string)
    - Before processing, we verify the booking is still in PENDING status
    - If already confirmed/failed/cancelled — we skip and return early
    - This makes repeated calls safe with no side effects
    """
    settings = get_settings()
    bid = uuid.UUID(booking_id)
    log = logger.bind(booking_id=booking_id, task="confirm_booking")

    log.info("task.started")

    factory = get_session_factory()
    async with factory() as session:
        repo = BookingRepository(session)
        booking = await repo.get_by_id(bid)

        if booking is None:
            log.warning("task.booking_not_found")
            return {"status": "skipped", "reason": "booking_not_found"}

        if booking.status != BookingStatus.PENDING:
            log.info(
                "task.skipped_not_pending",
                current_status=booking.status.value,
            )
            return {"status": "skipped", "reason": f"already_{booking.status.value}"}

        if random.random() < settings.task_failure_probability:
            log.warning("task.external_service_failure", attempt="simulated")
            await repo.update_status(
                booking_id=bid,
                status=BookingStatus.FAILED,
                failure_reason="External service unavailable (simulated failure)",
            )
            await session.commit()
            raise ExternalServiceError("Simulated external service failure")

        await _mock_external_notification(bid, booking.name)
        await repo.update_status(
            booking_id=bid,
            status=BookingStatus.CONFIRMED,
            notification_sent=True,
        )
        await session.commit()

        log.info("task.completed", final_status="confirmed")
        return {"status": "confirmed", "booking_id": booking_id}
