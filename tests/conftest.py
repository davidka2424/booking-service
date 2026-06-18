import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.booking import Booking, BookingStatus, ServiceType


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_broker():
    """Mock TaskIQ broker — tasks are not sent to Redis."""

    async def _kiq_side_effect(*args, **kwargs):
        mock_task = MagicMock()
        mock_task.task_id = str(uuid.uuid4())
        return mock_task

    mock_kiq = AsyncMock(side_effect=_kiq_side_effect)
    with patch("app.workers.tasks.booking.confirm_booking.kiq", mock_kiq):
        yield mock_kiq


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    mock_broker,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Test HTTP client with in-memory SQLite and mocked TaskIQ broker.
    """
    from app.db.session import get_db_session
    from app.main import create_app

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.state.limiter.enabled = False

    with patch("app.core.lifespan.create_db_engine", AsyncMock()), \
         patch("app.core.lifespan.dispose_db_engine", AsyncMock()), \
         patch("app.workers.broker.broker.startup", AsyncMock()), \
         patch("app.workers.broker.broker.shutdown", AsyncMock()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


def future_datetime(hours: int = 24) -> str:
    dt = datetime.now(tz=UTC) + timedelta(hours=hours)
    return dt.isoformat()


@pytest_asyncio.fixture
async def pending_booking(db_session: AsyncSession) -> Booking:
    from app.repositories.booking import BookingRepository

    repo = BookingRepository(db_session)
    booking = await repo.create(
        name="Test User",
        service_type=ServiceType.CONSULTATION,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=BookingStatus.PENDING,
    )
    await db_session.commit()
    return booking


@pytest_asyncio.fixture
async def confirmed_booking(db_session: AsyncSession) -> Booking:
    from app.repositories.booking import BookingRepository

    repo = BookingRepository(db_session)
    booking = await repo.create(
        name="Confirmed User",
        service_type=ServiceType.REPAIR,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=2),
        status=BookingStatus.CONFIRMED,
    )
    await db_session.commit()
    return booking