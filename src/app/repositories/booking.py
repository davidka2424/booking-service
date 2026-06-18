import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.booking import Booking, BookingStatus
from app.repositories.base import AbstractRepository


class BookingRepository(AbstractRepository[Booking]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, id: uuid.UUID) -> Booking | None:
        result = await self._session.execute(
            select(Booking).where(Booking.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> Booking:
        booking = Booking(**kwargs)
        self._session.add(booking)
        await self._session.flush()
        await self._session.refresh(booking)
        return booking

    async def delete(self, instance: Booking) -> None:
        await self._session.delete(instance)
        await self._session.flush()

    async def get_list(
        self,
        status: BookingStatus | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Booking], int]:
        query = select(Booking)
        count_query = select(func.count()).select_from(Booking)

        if status is not None:
            query = query.where(Booking.status == status)
            count_query = count_query.where(Booking.status == status)

        total_result = await self._session.execute(count_query)
        total: int = total_result.scalar_one()

        offset = (page - 1) * size
        query = query.order_by(Booking.created_at.desc()).offset(offset).limit(size)

        result = await self._session.execute(query)
        bookings = list(result.scalars().all())

        return bookings, total

    async def update_status(
        self,
        booking_id: uuid.UUID,
        status: BookingStatus,
        notification_sent: bool = False,
        failure_reason: str | None = None,
    ) -> Booking | None:
        booking = await self.get_by_id(booking_id)
        if booking is None:
            return None
        booking.status = status
        booking.notification_sent = notification_sent
        booking.failure_reason = failure_reason
        await self._session.flush()
        await self._session.refresh(booking)
        return booking

    async def set_task_id(
        self, booking_id: uuid.UUID, task_id: uuid.UUID
    ) -> None:
        stmt = (
            update(Booking)
            .where(Booking.id == booking_id)
            .values(task_id=task_id)
        )
        await self._session.execute(stmt)
        await self._session.flush()
