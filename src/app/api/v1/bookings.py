import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.exceptions import BookingCancellationError, BookingNotFoundError
from app.core.logging import get_logger
from app.db.models.booking import BookingStatus
from app.db.session import get_db_session
from app.repositories.booking import BookingRepository
from app.schemas.booking import (
    BookingCreate,
    BookingFilters,
    BookingListResponse,
    BookingResponse,
)
from app.services.booking import BookingService

logger = get_logger(__name__)
router = APIRouter(prefix="/bookings", tags=["bookings"])
_settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


def get_booking_service(
    session: Annotated[object, Depends(get_db_session)],
) -> BookingService:
    return BookingService(BookingRepository(session))  # type: ignore[arg-type]


ServiceDep = Annotated[BookingService, Depends(get_booking_service)]


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a booking",
    description="Creates a new booking and enqueues it for async confirmation.",
)
@limiter.limit(f"{_settings.rate_limit_per_minute}/minute")
async def create_booking(
    request: Request,
    payload: BookingCreate,
    service: ServiceDep,
) -> BookingResponse:
    try:
        return await service.create_booking(payload)
    except Exception as exc:
        logger.error("booking.create_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking",
        ) from exc


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking by ID",
)
async def get_booking(
    booking_id: uuid.UUID,
    service: ServiceDep,
) -> BookingResponse:
    try:
        return await service.get_booking(booking_id)
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=BookingListResponse,
    summary="List bookings with filtering and pagination",
)
async def list_bookings(
    service: ServiceDep,
    booking_status: Annotated[
        BookingStatus | None,
        Query(alias="status", description="Filter by status"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
) -> BookingListResponse:
    filters = BookingFilters(status=booking_status, page=page, size=size)
    return await service.list_bookings(filters)


@router.delete(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Cancel a booking",
    description=(
        "Cancels a booking. Only bookings in 'pending' status can be cancelled."
    ),
)
async def cancel_booking(
    booking_id: uuid.UUID,
    service: ServiceDep,
) -> BookingResponse:
    try:
        return await service.cancel_booking(booking_id)
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except BookingCancellationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
