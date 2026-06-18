class BookingServiceError(Exception):
    """Base exception for booking service."""


class BookingNotFoundError(BookingServiceError):
    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id
        super().__init__(f"Booking '{booking_id}' not found")


class BookingCancellationError(BookingServiceError):
    def __init__(self, booking_id: str, status: str) -> None:
        self.booking_id = booking_id
        self.status = status
        super().__init__(
            f"Booking '{booking_id}' cannot be cancelled: current status is '{status}'"
        )


class ExternalServiceError(BookingServiceError):
    """Raised when an external service call fails (simulated)."""
