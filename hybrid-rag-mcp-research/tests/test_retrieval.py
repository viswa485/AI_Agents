from pathlib import Path

from hybrid_rag.evaluation import evaluate_retrieval, load_eval_dataset
from hybrid_rag.ingest import chunk_text, load_documents
from hybrid_rag.retrieval import SearchEngine, reciprocal_rank_fusion

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_chunk_text_handles_empty_and_overlap() -> None:
    assert chunk_text("   ") == []
    chunks = chunk_text("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=2)
    assert chunks[0] == "abcdefghij"
    assert chunks[1].startswith("ijklmnop")


def test_reciprocal_rank_fusion_combines_rankings() -> None:
    scores = reciprocal_rank_fusion([[1, 2], [2, 3]], weights=[1.0, 1.0])
    assert scores[2] > scores[1]
    assert scores[2] > scores[3]


def test_bm25_search_returns_relevant_source() -> None:
    documents = load_documents(PROJECT_ROOT / "data" / "sample_corpus")
    engine = SearchEngine(documents)
    hits = engine.search("reciprocal rank fusion combines retrieval rankings", top_k=3)
    assert hits
    assert hits[0].metadata["source"] == "rag_architecture.md"


def test_metadata_filter_is_applied() -> None:
    documents = load_documents(PROJECT_ROOT / "data" / "sample_corpus")
    engine = SearchEngine(documents)
    hits = engine.search("agent checkpointing", filters={"source": "agent_state_and_tools.md"})
    assert hits
    assert all(hit.metadata["source"] == "agent_state_and_tools.md" for hit in hits)


def test_reference_evaluation_returns_defined_metrics() -> None:
    documents = load_documents(PROJECT_ROOT / "data" / "sample_corpus")
    assert len(documents) == 3
    assert all(document.doc_id.endswith("#0") for document in documents)
    engine = SearchEngine(documents)
    dataset = load_eval_dataset(PROJECT_ROOT / "data" / "eval_dataset.jsonl")
    result = evaluate_retrieval(engine, dataset, k=3)
    assert result["query_count"] == 50
    assert 0.0 <= result["recall_at_k"] <= 1.0
    assert 0.0 <= result["mrr"] <= 1.0
