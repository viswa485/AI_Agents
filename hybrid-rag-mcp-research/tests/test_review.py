import json
from pathlib import Path

from hybrid_rag.agent import build_research_agent
from hybrid_rag.evaluation import load_eval_dataset
from hybrid_rag.ingest import load_documents
from hybrid_rag.retrieval import SearchEngine
from hybrid_rag.review import run_reference_review

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_reference_review_runs_all_50_queries_and_exports_audit_file(tmp_path: Path) -> None:
    engine = SearchEngine(load_documents(PROJECT_ROOT / "data" / "sample_corpus"))
    agent = build_research_agent(engine)
    dataset = load_eval_dataset(PROJECT_ROOT / "data" / "eval_dataset.jsonl")
    output_path = tmp_path / "review" / "results.jsonl"

    summary = run_reference_review(
        agent,
        dataset,
        output_path,
        top_k=3,
        context_max_chars=1200,
        context_max_chunks=2,
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert summary["query_count"] == 50
    assert len(rows) == 50
    assert 0.0 <= summary["recall_at_k"] <= 1.0
    assert 0.0 <= summary["mrr"] <= 1.0
    assert rows[0]["faithfulness_review"] == "pending_manual_review"
    assert all(row["context_stats"]["retained_chars"] <= 1200 for row in rows)
