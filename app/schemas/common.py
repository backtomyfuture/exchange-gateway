"""Common pagination schemas for all list endpoints.

Usage:
    @router.get("/items")
    async def list_items(params: Annotated[PageParams, Depends()]):
        items = await Item.all().offset(params.offset).limit(params.size)
        total = await Item.all().count()
        return Page(items=items, total=total, page=params.page, size=params.size)
"""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PageParams(BaseModel):
    """Standardized pagination query parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(20, ge=1, description="Items per page (max 100, clamped)")

    # Backward-compat aliases: accept skip/limit and convert to page/size
    skip: int | None = Field(None, exclude=True, description="Deprecated: use page")
    limit: int | None = Field(None, exclude=True, description="Deprecated: use size")

    @model_validator(mode="after")
    def apply_legacy_params(self) -> "PageParams":
        # Clamp size to 100 max
        self.size = min(self.size, 100)
        if self.limit is not None:
            self.size = min(self.limit, 100)
        if self.skip is not None and self.size > 0:
            self.page = (self.skip // self.size) + 1
        return self

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.size) if self.size > 0 else 0
