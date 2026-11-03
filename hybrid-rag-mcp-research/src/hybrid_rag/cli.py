from __future__ import annotations

import argparse
import json
from pathlib import Path

from hybrid_rag.agent import ask_question, build_research_agent
from hybrid_rag.evaluation import evaluate_retrieval, load_eval_dataset
from hybrid_rag.ingest import load_documents
from hybrid_rag.review import run_reference_review
from hybrid_rag.retrieval import SearchEngine

DEFAULT_CORPUS = Path("data/sample_corpus")
DEFAULT_EVAL = Path("data/eval_dataset.jsonl")


def _engine(args: argparse.Namespace) -> SearchEngine:
    documents = load_documents(args.corpus)
    return SearchEngine(
        documents,
        embedding_model=args.embedding_model if args.dense else None,
        reranker_model=args.reranker_model if args.rerank else None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hybrid RAG and stateful research prototype")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--dense", action="store_true", help="Enable SentenceTransformer embeddings")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--rerank", action="store_true", help="Enable cross-encoder reranking")
    parser.add_argument("--reranker-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    commands = parser.add_subparsers(dest="command", required=True)

    search = commands.add_parser("search", help="Retrieve matching chunks")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=5)

    ask = commands.add_parser("ask", help="Run the checkpointed LangGraph workflow")
    ask.add_argument("question")
    ask.add_argument("--thread-id", default="local-research-session")
    ask.add_argument("--top-k", type=int, default=5)
    ask.add_argument("--context-max-chars", type=int, default=3000)
    ask.add_argument("--context-max-chunks", type=int, default=5)

    evaluate = commands.add_parser("evaluate", help="Evaluate retrieval against labelled JSONL")
    evaluate.add_argument("--dataset", type=Path, default=DEFAULT_EVAL)
    evaluate.add_argument("--k", type=int, default=5)

    review = commands.add_parser(
        "review",
        help="Run every labelled question through the graph and export an answer/evidence review file",
    )
    review.add_argument("--dataset", type=Path, default=DEFAULT_EVAL)
    review.add_argument("--output", type=Path, default=Path("results/reference_review.jsonl"))
    review.add_argument("--top-k", type=int, default=5)
    review.add_argument("--context-max-chars", type=int, default=3000)
    review.add_argument("--context-max-chunks", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = _engine(args)
    if args.command == "search":
        results = [hit.to_dict() for hit in engine.search(args.query, top_k=args.top_k)]
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.command == "ask":
        agent = build_research_agent(engine)
        result = ask_question(
            agent,
            args.question,
            thread_id=args.thread_id,
            top_k=args.top_k,
            context_max_chars=args.context_max_chars,
            context_max_chunks=args.context_max_chunks,
        )
        print(result["answer"])
        stats = result.get("context_stats", {})
        if stats:
            print(
                "\nContext budget: "
                f"{stats['retained_chars']}/{stats['original_chars']} chars; "
                f"~{stats['estimated_tokens']} tokens; "
                f"{stats['retained_chunks']}/{stats['input_chunks']} chunks retained."
            )
    elif args.command == "evaluate":
        dataset = load_eval_dataset(args.dataset)
        result = evaluate_retrieval(engine, dataset, k=args.k)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "review":
        dataset = load_eval_dataset(args.dataset)
        agent = build_research_agent(engine)
        result = run_reference_review(
            engine,
            agent,
            dataset,
            args.output,
            top_k=args.top_k,
            context_max_chars=args.context_max_chars,
            context_max_chunks=args.context_max_chunks,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
