from pathlib import Path

from hybrid_rag.agent import ask_question, build_research_agent
from hybrid_rag.ingest import load_documents
from hybrid_rag.retrieval import SearchEngine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_research_agent_returns_source_linked_evidence() -> None:
    engine = SearchEngine(load_documents(PROJECT_ROOT / "data" / "sample_corpus"))
    agent = build_research_agent(engine)
    result = ask_question(
        agent,
        "How does checkpointing work in a stateful agent workflow?",
        thread_id="test-agent-session",
        top_k=3,
        min_hits=1,
        context_max_chars=1200,
        context_max_chunks=2,
    )
    assert "answer" in result
    assert "source:" in result["answer"] or "[" in result["answer"]
    assert result["hits"]
    assert result["context_stats"]["retained_chars"] <= 1200
    assert result["context_stats"]["retained_chunks"] <= 2


def test_agent_rejects_empty_question() -> None:
    engine = SearchEngine(load_documents(PROJECT_ROOT / "data" / "sample_corpus"))
    agent = build_research_agent(engine)
    try:
        ask_question(agent, "   ")
    except ValueError as exc:
        assert "question must not be empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty question")


def test_graph_resumes_from_an_in_memory_checkpoint() -> None:
    engine = SearchEngine(load_documents(PROJECT_ROOT / "data" / "sample_corpus"))
    agent = build_research_agent(engine, interrupt_before=["synthesis_agent"])
    config = {"configurable": {"thread_id": "resume-test-session"}}

    paused = agent.invoke(
        {
            "question": "How does a thread identifier store graph state?",
            "query": "How does a thread identifier store graph state?",
            "top_k": 3,
            "min_hits": 1,
            "context_max_chars": 1200,
            "context_max_chunks": 2,
            "rewrite_count": 0,
        },
        config=config,
    )
    assert "answer" not in paused
    snapshot = agent.get_state(config)
    assert snapshot.next == ("synthesis_agent",)

    resumed = agent.invoke(None, config=config)
    assert resumed["answer"]
    assert "source:" in resumed["answer"]
