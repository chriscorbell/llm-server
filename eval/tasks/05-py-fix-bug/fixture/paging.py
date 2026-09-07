"""Offset pagination over an in-memory sequence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def total_pages(self) -> int:
        return self.total // self.per_page

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def paginate(items: Sequence[T], page: int = 1, per_page: int = 10) -> Page:
    if page < 1:
        raise ValueError("page is 1-indexed")
    if per_page < 1:
        raise ValueError("per_page must be positive")
    start = (page - 1) * per_page
    return Page(
        items=list(items[start : start + per_page]),
        page=page,
        per_page=per_page,
        total=len(items),
    )
