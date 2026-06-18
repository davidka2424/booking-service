import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExternalServiceError
from app.db.models.booking import Booking, BookingStatus, ServiceType


def make_booking(status: BookingStatus = BookingStatus.PENDING) -> MagicMock:
    booking = MagicMock(spec=Booking)
    booking.id = uuid.uuid4()
    booking.name = "Test User"
    booking.status = status
    booking.service_type = ServiceType.CONSULTATION
    booking.scheduled_at = datetime.now(tz=UTC) + timedelta(days=1)
    return booking


async def _call_task(booking_id: str) -> dict:
    from app.workers.tasks.booking import confirm_booking

    return await confirm_booking.original_func(booking_id)


class TestConfirmBookingTask:
    async def test_task_success_path(self) -> None:
        booking = make_booking(BookingStatus.PENDING)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = booking
        mock_repo.update_status.return_value = booking

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
            patch("app.workers.tasks.booking.random.random", return_value=0.99),
        ):
            result = await _call_task(str(booking.id))

        assert result["status"] == "confirmed"
        mock_repo.update_status.assert_awaited_once()
        call_kwargs = mock_repo.update_status.call_args.kwargs
        assert call_kwargs["status"] == BookingStatus.CONFIRMED
        assert call_kwargs["notification_sent"] is True

    async def test_task_failure_path(self) -> None:
        booking = make_booking(BookingStatus.PENDING)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = booking
        mock_repo.update_status.return_value = booking

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
            patch("app.workers.tasks.booking.random.random", return_value=0.01),
        ):
            with pytest.raises(ExternalServiceError):
                await _call_task(str(booking.id))

        mock_repo.update_status.assert_awaited_once()
        call_kwargs = mock_repo.update_status.call_args.kwargs
        assert call_kwargs["status"] == BookingStatus.FAILED
        assert call_kwargs["failure_reason"] is not None

    async def test_task_idempotency_already_confirmed(self) -> None:
        booking = make_booking(BookingStatus.CONFIRMED)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = booking

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _call_task(str(booking.id))

        assert result["status"] == "skipped"
        assert "confirmed" in result["reason"]
        mock_repo.update_status.assert_not_awaited()

    async def test_task_idempotency_already_cancelled(self) -> None:
        booking = make_booking(BookingStatus.CANCELLED)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = booking

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _call_task(str(booking.id))

        assert result["status"] == "skipped"
        mock_repo.update_status.assert_not_awaited()

    async def test_task_booking_not_found(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
        ):
            result = await _call_task(str(uuid.uuid4()))

        assert result["status"] == "skipped"
        assert result["reason"] == "booking_not_found"

    async def test_mock_notification_is_called_on_success(self) -> None:
        booking = make_booking(BookingStatus.PENDING)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = booking
        mock_repo.update_status.return_value = booking

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)
        mock_notify = AsyncMock()

        with (
            patch(
                "app.workers.tasks.booking.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "app.workers.tasks.booking.BookingRepository",
                return_value=mock_repo,
            ),
            patch("app.workers.tasks.booking.random.random", return_value=0.99),
            patch(
                "app.workers.tasks.booking._mock_external_notification",
                mock_notify,
            ),
        ):
            await _call_task(str(booking.id))

        mock_notify.assert_awaited_once_with(booking.id, booking.name)