from __future__ import annotations

import os
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from hybrid_rag.context import prune_evidence
from hybrid_rag.observability import trace_span
from hybrid_rag.retrieval import SearchEngine


class ResearchState(TypedDict, total=False):
    question: str
    query: str
    top_k: int
    min_hits: int
    context_max_chars: int
    context_max_chunks: int
    rewrite_count: int
    hits: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    context_stats: dict[str, int]
    critique: str
    answer: str


@trace_span("research.llm_completion", as_type="generation")
def _optional_llm_response(system_prompt: str, user_prompt: str) -> str | None:
    """Call an OpenAI-compatible model only when explicitly configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            'OPENAI_API_KEY is set but the SDK is missing; install with pip install -e ".[llm]".'
        ) from exc

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    response = client.chat.completions.create(
        model=model_name,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    usage = getattr(response, "usage", None)
    if usage is not None:
        try:
            from langfuse import get_client

            get_client().update_current_generation(
                model=model_name,
                usage_details={
                    "prompt_tokens": int(usage.prompt_tokens),
                    "completion_tokens": int(usage.completion_tokens),
                    "total_tokens": int(usage.total_tokens),
                },
            )
        except (ImportError, AttributeError, RuntimeError):
            # The model response must remain usable if optional tracing is unavailable.
            pass

    content = response.choices[0].message.content
    return content.strip() if content else None


def build_research_agent(engine: SearchEngine):
    """Build a checkpointed graph with specialist stages.

    When OPENAI_API_KEY is configured and the optional OpenAI SDK is installed,
    query rewriting, evidence critique and synthesis use separate LLM calls.
    Otherwise, deterministic local fallbacks keep the prototype usable offline.
    """

    @trace_span("research.retrieval_specialist", as_type="retriever")
    def retrieval_specialist(state: ResearchState) -> dict[str, Any]:
        hits = engine.search(state.get("query", state["question"]), top_k=state.get("top_k", 5))
        return {"hits": [hit.to_dict() for hit in hits]}

    @trace_span("research.evidence_specialist")
    def evidence_specialist(state: ResearchState) -> dict[str, Any]:
        evidence = [
            {
                "doc_id": hit["doc_id"],
                "source": hit.get("metadata", {}).get("source", "unknown"),
                "excerpt": hit["text"],
                "retrieval_score": hit["score"],
            }
            for hit in state.get("hits", [])
        ]
        return {"evidence": evidence}

    @trace_span("research.context_pruner")
    def context_pruner(state: ResearchState) -> dict[str, Any]:
        evidence, stats = prune_evidence(
            state.get("evidence", []),
            max_chunks=state.get("context_max_chunks", 5),
            max_chars=state.get("context_max_chars", 6000),
        )
        return {"evidence": evidence, "context_stats": stats}

    @trace_span("research.critic_agent", as_type="agent")
    def critic_agent(state: ResearchState) -> dict[str, Any]:
        evidence = state.get("evidence", [])
        fallback = (
            "sufficient" if len(evidence) >= state.get("min_hits", 2) else "insufficient"
        )
        if not evidence:
            return {"critique": fallback}

        prompt = (
            "Decide whether the supplied evidence contains enough directly relevant material "
            "to address the question. Reply with exactly SUFFICIENT or INSUFFICIENT. "
            "Do not infer facts not present in evidence.\n\n"
            f"Question: {state['question']}\nEvidence:\n"
            + "\n".join(f"[{item['doc_id']}] {item['excerpt']}" for item in evidence)
        )
        response = _optional_llm_response(
            "You are a strict evidence-quality reviewer.", prompt
        )
        if response:
            normalized = response.strip().upper()
            return {
                "critique": "sufficient" if normalized.startswith("SUFFICIENT") else "insufficient"
            }
        return {"critique": fallback}

    def route_after_critic(state: ResearchState) -> str:
        can_rewrite = state.get("rewrite_count", 0) < 1
        if state.get("critique") == "insufficient" and can_rewrite:
            return "rewrite"
        return "synthesize"

    @trace_span("research.query_rewriter_agent", as_type="agent")
    def query_rewriter_agent(state: ResearchState) -> dict[str, Any]:
        question = state.get("question", state.get("query", ""))
        prompt = (
            "Rewrite the user question as one concise search query for a technical knowledge "
            "base. Preserve named entities and technical terms. Do not answer the question. "
            f"\n\nQuestion: {question}"
        )
        response = _optional_llm_response(
            "You are a retrieval query-rewriting specialist.", prompt
        )
        expanded = response or f"{question} architecture implementation design evaluation"
        return {
            "query": expanded[:1000],
            "rewrite_count": state.get("rewrite_count", 0) + 1,
        }

    @trace_span("research.synthesis_agent", as_type="agent")
    def synthesis_agent(state: ResearchState) -> dict[str, Any]:
        evidence = state.get("evidence", [])
        if not evidence:
            return {
                "answer": (
                    "No supporting passages were retrieved. Try a more specific question "
                    "or add relevant documents to the corpus."
                )
            }

        evidence_text = "\n\n".join(
            f"SOURCE {item['doc_id']}\n{item['excerpt']}" for item in evidence
        )
        prompt = (
            "Answer the question using only the supplied evidence. Every factual paragraph "
            "must contain one or more exact source identifiers in square brackets, such as "
            "[guide.md#0]. If evidence is insufficient, say so. Do not invent sources or facts."
            f"\n\nQuestion: {state['question']}\n\nEvidence:\n{evidence_text}"
        )
        response = _optional_llm_response(
            "You are a cautious research synthesis specialist. Ground every claim in evidence.",
            prompt,
        )
        if response:
            return {"answer": response}
        bullets = [
            f"- {item['excerpt'].strip()} [source: {item['doc_id']}]"
            for item in evidence
        ]
        return {
            "answer": (
                "Retrieved evidence (extractive fallback; verify each cited source):\n"
                + "\n".join(bullets)
            )
        }

    graph = StateGraph(ResearchState)
    graph.add_node("retrieval_specialist", retrieval_specialist)
    graph.add_node("evidence_specialist", evidence_specialist)
    graph.add_node("context_pruner", context_pruner)
    graph.add_node("critic_agent", critic_agent)
    graph.add_node("query_rewriter_agent", query_rewriter_agent)
    graph.add_node("synthesis_agent", synthesis_agent)
    graph.add_edge(START, "retrieval_specialist")
    graph.add_edge("retrieval_specialist", "evidence_specialist")
    graph.add_edge("evidence_specialist", "context_pruner")
    graph.add_edge("context_pruner", "critic_agent")
    graph.add_conditional_edges(
        "critic_agent",
        route_after_critic,
        {"rewrite": "query_rewriter_agent", "synthesize": "synthesis_agent"},
    )
    graph.add_edge("query_rewriter_agent", "retrieval_specialist")
    graph.add_edge("synthesis_agent", END)
    return graph.compile(checkpointer=MemorySaver())


def ask_question(
    agent,
    question: str,
    *,
    thread_id: str = "local-research-session",
    top_k: int = 5,
    min_hits: int = 2,
    context_max_chars: int = 6000,
    context_max_chunks: int = 5,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("question must not be empty")
    if top_k < 1 or top_k > 20:
        raise ValueError("top_k must be between 1 and 20")
    if min_hits < 1:
        raise ValueError("min_hits must be greater than zero")
    return agent.invoke(
        {
            "question": question,
            "query": question,
            "top_k": top_k,
            "min_hits": min_hits,
            "context_max_chars": context_max_chars,
            "context_max_chunks": context_max_chunks,
            "rewrite_count": 0,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
