import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.db.models.booking import Booking
from tests.conftest import future_datetime


class TestCreateBooking:
    async def test_create_booking_success(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/bookings",
            json={
                "name": "Ivan Petrov",
                "scheduled_at": future_datetime(48),
                "service_type": "consultation",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Ivan Petrov"
        assert data["service_type"] == "consultation"
        assert data["status"] == "pending"
        assert data["notification_sent"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_create_booking_all_service_types(
        self, client: AsyncClient
    ) -> None:
        service_types = [
            "consultation",
            "repair",
            "installation",
            "maintenance",
            "inspection",
        ]
        for stype in service_types:
            response = await client.post(
                "/api/v1/bookings",
                json={
                    "name": "Test User",
                    "scheduled_at": future_datetime(24),
                    "service_type": stype,
                },
            )
            assert response.status_code == 201, f"Failed for service_type={stype}"

    async def test_create_booking_name_too_short(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/bookings",
            json={
                "name": "A",
                "scheduled_at": future_datetime(),
                "service_type": "consultation",
            },
        )
        assert response.status_code == 422

    async def test_create_booking_past_datetime(self, client: AsyncClient) -> None:
        past = (datetime.now(tz=UTC) - timedelta(hours=1)).isoformat()
        response = await client.post(
            "/api/v1/bookings",
            json={
                "name": "Ivan Petrov",
                "scheduled_at": past,
                "service_type": "consultation",
            },
        )
        assert response.status_code == 422

    async def test_create_booking_invalid_service_type(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/bookings",
            json={
                "name": "Ivan Petrov",
                "scheduled_at": future_datetime(),
                "service_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    async def test_create_booking_missing_fields(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/bookings", json={"name": "Ivan Petrov"}
        )
        assert response.status_code == 422

    async def test_create_booking_no_timezone(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/bookings",
            json={
                "name": "Ivan Petrov",
                "scheduled_at": "2099-01-01T10:00:00",
                "service_type": "consultation",
            },
        )
        assert response.status_code == 422


class TestGetBooking:
    async def test_get_booking_success(
        self, client: AsyncClient, pending_booking: Booking
    ) -> None:
        response = await client.get(f"/api/v1/bookings/{pending_booking.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(pending_booking.id)
        assert data["status"] == "pending"

    async def test_get_booking_not_found(self, client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/bookings/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_booking_invalid_uuid(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings/not-a-valid-uuid")
        assert response.status_code == 422


class TestListBookings:
    async def test_list_bookings_empty(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_list_bookings_returns_created(
        self, client: AsyncClient, pending_booking: Booking
    ) -> None:
        response = await client.get("/api/v1/bookings")
        assert response.status_code == 200
        ids = [item["id"] for item in response.json()["items"]]
        assert str(pending_booking.id) in ids

    async def test_list_bookings_filter_by_status(
        self,
        client: AsyncClient,
        pending_booking: Booking,  # noqa: ARG002
        confirmed_booking: Booking,  # noqa: ARG002
    ) -> None:
        response = await client.get("/api/v1/bookings?status=pending")
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(item["status"] == "pending" for item in items)

        response = await client.get("/api/v1/bookings?status=confirmed")
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(item["status"] == "confirmed" for item in items)

    async def test_list_bookings_pagination(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

    async def test_list_bookings_invalid_status(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings?status=unknown")
        assert response.status_code == 422

    async def test_list_bookings_size_too_large(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings?size=999")
        assert response.status_code == 422

    async def test_list_bookings_page_zero(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/bookings?page=0")
        assert response.status_code == 422


class TestCancelBooking:
    async def test_cancel_pending_booking_success(
        self, client: AsyncClient, pending_booking: Booking
    ) -> None:
        response = await client.delete(f"/api/v1/bookings/{pending_booking.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["id"] == str(pending_booking.id)

    async def test_cancel_confirmed_booking_returns_409(
        self, client: AsyncClient, confirmed_booking: Booking
    ) -> None:
        response = await client.delete(f"/api/v1/bookings/{confirmed_booking.id}")
        assert response.status_code == 409
        assert "confirmed" in response.json()["detail"].lower()

    async def test_cancel_already_cancelled_booking(
        self, client: AsyncClient, pending_booking: Booking
    ) -> None:
        resp1 = await client.delete(f"/api/v1/bookings/{pending_booking.id}")
        assert resp1.status_code == 200

        resp2 = await client.delete(f"/api/v1/bookings/{pending_booking.id}")
        assert resp2.status_code == 409

    async def test_cancel_nonexistent_booking(self, client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/bookings/{fake_id}")
        assert response.status_code == 404


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"