import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class AbstractRepository(ABC, Generic[ModelT]):
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
