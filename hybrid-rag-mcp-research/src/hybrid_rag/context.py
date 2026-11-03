from __future__ import annotations

from typing import Any


def prune_evidence(
    evidence: list[dict[str, Any]],
    *,
    max_chunks: int = 5,
    max_chars: int = 6000,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep the highest-ranked evidence within an explicit character budget.

    The token count is an intentionally rough estimate (four characters per token),
    not a substitute for the tokenizer used by a particular model.
    """
    if max_chunks <= 0:
        raise ValueError("max_chunks must be greater than zero")
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    original_chars = sum(len(str(item.get("excerpt", ""))) for item in evidence)
    retained: list[dict[str, Any]] = []
    retained_chars = 0
    seen_text: set[str] = set()

    for item in evidence:
        if len(retained) >= max_chunks:
            break
        excerpt = str(item.get("excerpt", "")).strip()
        normalized = " ".join(excerpt.lower().split())
        if not normalized or normalized in seen_text:
            continue
        remaining = max_chars - retained_chars
        if remaining <= 0:
            break
        excerpt = excerpt[:remaining].rstrip()
        if not excerpt:
            break
        seen_text.add(normalized)
        retained.append({**item, "excerpt": excerpt})
        retained_chars += len(excerpt)

    stats = {
        "input_chunks": len(evidence),
        "retained_chunks": len(retained),
        "removed_chunks": max(0, len(evidence) - len(retained)),
        "original_chars": original_chars,
        "retained_chars": retained_chars,
        "estimated_tokens": (retained_chars + 3) // 4,
    }
    return retained, stats
