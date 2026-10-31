"""Shared response shapes."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    results: list[T]
    pagination: PaginationMeta


class AreaValue(BaseModel):
    value: str | None = None
    unit: str = "sq_ft"
    basis: str | None = None


class MessageOut(BaseModel):
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
