from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from hybrid_rag.agent import ask_question


def run_reference_review(
    agent: Any,
    dataset: list[dict[str, Any]],
    output_path: str | Path,
    *,
    top_k: int = 5,
    context_max_chars: int = 3000,
    context_max_chunks: int = 5,
) -> dict[str, Any]:
    """Run labelled questions through the graph and export an auditable review file.

    Retrieval metrics are calculated automatically. Faithfulness is deliberately left
    for human review; a citation string or an LLM self-critique is not proof of truth.
    """
    if not dataset:
        raise ValueError("Review dataset must contain at least one query")
    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    context_tokens: list[int] = []
    rewritten = 0

    for index, record in enumerate(dataset, start=1):
        query = str(record.get("query", "")).strip()
        relevant = set(record.get("relevant_doc_ids", []))
        if not query:
            raise ValueError(f"Review record {index} has an empty query")
        if not relevant:
            raise ValueError(f"Review record {index} has no relevant_doc_ids")

        result = ask_question(
            agent,
            query,
            thread_id=f"reference-review-{index:03d}",
            top_k=top_k,
            context_max_chars=context_max_chars,
            context_max_chunks=context_max_chunks,
        )
        returned_ids = [hit["doc_id"] for hit in result.get("hits", [])]
        found = relevant.intersection(returned_ids)
        recall = len(found) / len(relevant)
        reciprocal_rank = next(
            (
                1.0 / rank
                for rank, doc_id in enumerate(returned_ids, start=1)
                if doc_id in relevant
            ),
            0.0,
        )
        stats = result.get("context_stats", {})
        context_tokens.append(int(stats.get("estimated_tokens", 0)))
        rewrite_count = int(result.get("rewrite_count", 0))
        rewritten += int(rewrite_count > 0)

        rows.append(
            {
                "case_id": index,
                "query": query,
                "retrieval_query": result.get("query", query),
                "rewrite_count": rewrite_count,
                "critic_outcome": result.get("critique", "not_recorded"),
                "returned_doc_ids": returned_ids,
                "relevant_doc_ids": sorted(relevant),
                "recall_at_k": recall,
                "reciprocal_rank": reciprocal_rank,
                "context_stats": stats,
                "evidence": [
                    {
                        "doc_id": item["doc_id"],
                        "excerpt": item["excerpt"],
                    }
                    for item in result.get("evidence", [])
                ],
                "answer": result.get("answer", ""),
                "faithfulness_review": "pending_manual_review",
            }
        )
        recalls.append(recall)
        reciprocal_ranks.append(reciprocal_rank)

    with destination.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "query_count": len(rows),
        "recall_at_k": mean(recalls),
        "mrr": mean(reciprocal_ranks),
        "queries_rewritten": rewritten,
        "mean_context_token_estimate": mean(context_tokens),
        "output_path": str(destination),
        "faithfulness_review": "manual review required; no automatic faithfulness score is claimed",
    }
