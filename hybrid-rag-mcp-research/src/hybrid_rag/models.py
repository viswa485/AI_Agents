from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Document:
    """A text chunk with a stable identifier and source metadata."""

    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A retrieved document and the ranking signals used to select it."""

    doc_id: str
    text: str
    metadata: dict[str, Any]
    score: float
    bm25_rank: int | None = None
    dense_rank: int | None = None
    rerank_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
