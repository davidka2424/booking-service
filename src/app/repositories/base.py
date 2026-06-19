import uuid
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class AbstractRepository[ModelT: Base](ABC):
    """Abstract base repository defining the data access contract."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, **kwargs: object) -> ModelT:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, instance: ModelT) -> None:
        raise NotImplementedError
