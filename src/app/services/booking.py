import uuid
from math import ceil

from app.core.exceptions import BookingCancellationError, BookingNotFoundError
from app.core.logging import get_logger
from app.db.models.booking import BookingStatus
from app.repositories.booking import BookingRepository
from app.schemas.booking import (
    BookingCreate,
    BookingFilters,
    BookingListResponse,
    BookingResponse,
)
from app.workers.tasks.booking import confirm_booking

logger = get_logger(__name__)


class BookingService:
    def __init__(self, repo: BookingRepository) -> None:
        self._repo = repo

    async def create_booking(self, data: BookingCreate) -> BookingResponse:
        log = logger.bind(service_type=data.service_type, customer=data.name)
        log.info("booking.creating")

        booking = await self._repo.create(
            name=data.name,
            scheduled_at=data.scheduled_at,
            service_type=data.service_type,
            status=BookingStatus.PENDING,
        )

        task = await confirm_booking.kiq(str(booking.id))
        await self._repo.set_task_id(booking.id, uuid.UUID(task.task_id))

        refreshed = await self._repo.get_by_id(booking.id)
        assert refreshed is not None

        log.info(
            "booking.created",
            booking_id=str(booking.id),
            task_id=task.task_id,
        )
        return BookingResponse.model_validate(refreshed)

    async def get_booking(self, booking_id: uuid.UUID) -> BookingResponse:
        booking = await self._repo.get_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(str(booking_id))
        return BookingResponse.model_validate(booking)

    async def list_bookings(self, filters: BookingFilters) -> BookingListResponse:
        bookings, total = await self._repo.get_list(
            status=filters.status,
            page=filters.page,
            size=filters.size,
        )
        pages = ceil(total / filters.size) if total > 0 else 1
        return BookingListResponse(
            items=[BookingResponse.model_validate(b) for b in bookings],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    async def cancel_booking(self, booking_id: uuid.UUID) -> BookingResponse:
        booking = await self._repo.get_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(str(booking_id))

        if booking.status != BookingStatus.PENDING:
            raise BookingCancellationError(str(booking_id), booking.status.value)

        updated = await self._repo.update_status(
            booking_id=booking_id,
            status=BookingStatus.CANCELLED,
        )
        logger.info("booking.cancelled", booking_id=str(booking_id))
        assert updated is not None
        return BookingResponse.model_validate(updated)