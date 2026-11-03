import pytest

from hybrid_rag.context import prune_evidence


def test_prune_evidence_respects_chunk_and_character_budgets() -> None:
    rows = [
        {"doc_id": "a#0", "excerpt": "A" * 100},
        {"doc_id": "b#0", "excerpt": "B" * 100},
        {"doc_id": "c#0", "excerpt": "C" * 100},
    ]
    kept, stats = prune_evidence(rows, max_chunks=2, max_chars=150)
    assert len(kept) == 2
    assert sum(len(row["excerpt"]) for row in kept) == 150
    assert stats["estimated_tokens"] == 38
    assert stats["removed_chunks"] == 1


def test_prune_evidence_deduplicates_repeated_passages() -> None:
    rows = [
        {"doc_id": "a#0", "excerpt": "Same text"},
        {"doc_id": "b#0", "excerpt": " same   text "},
    ]
    kept, stats = prune_evidence(rows)
    assert len(kept) == 1
    assert stats["removed_chunks"] == 1


def test_prune_evidence_rejects_invalid_budgets() -> None:
    with pytest.raises(ValueError):
        prune_evidence([], max_chars=0)
    with pytest.raises(ValueError):
        prune_evidence([], max_chunks=0)
