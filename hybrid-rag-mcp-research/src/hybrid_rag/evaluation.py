from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hybrid_rag.retrieval import SearchEngine


def load_eval_dataset(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(record.get("relevant_doc_ids"), list):
            raise TypeError(f"Line {line_number} must contain relevant_doc_ids as a list")
        records.append(record)
    return records


def evaluate_retrieval(
    engine: SearchEngine,
    dataset: list[dict[str, Any]],
    *,
    k: int = 5,
) -> dict[str, Any]:
    """Calculate Recall@K and mean reciprocal rank for labelled queries."""
    if not dataset:
        raise ValueError("Evaluation dataset must contain at least one query")
    if k <= 0:
        raise ValueError("k must be greater than zero")

    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    per_query: list[dict[str, Any]] = []

    for row in dataset:
        relevant = set(row["relevant_doc_ids"])
        hits = engine.search(row["query"], top_k=k)
        returned = [hit.doc_id for hit in hits]
        found = relevant.intersection(returned)
        recalls.append(len(found) / len(relevant) if relevant else 0.0)
        reciprocal = next(
            (1.0 / rank for rank, doc_id in enumerate(returned, start=1) if doc_id in relevant),
            0.0,
        )
        reciprocal_ranks.append(reciprocal)
        per_query.append(
            {
                "query": row["query"],
                "returned_doc_ids": returned,
                "relevant_doc_ids": sorted(relevant),
                "recall_at_k": recalls[-1],
                "reciprocal_rank": reciprocal,
            }
        )

    return {
        "query_count": len(dataset),
        "k": k,
        "recall_at_k": sum(recalls) / len(recalls),
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "per_query": per_query,
    }
