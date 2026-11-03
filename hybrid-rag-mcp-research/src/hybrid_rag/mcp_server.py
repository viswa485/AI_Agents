from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from hybrid_rag.agent import ask_question, build_research_agent
from hybrid_rag.ingest import load_documents
from hybrid_rag.retrieval import SearchEngine


def create_server(corpus_dir: str | Path) -> FastMCP:
    documents = load_documents(corpus_dir)
    engine = SearchEngine(documents)
    agent = build_research_agent(engine)
    server = FastMCP("hybrid-rag-research")

    @server.tool()
    def search_documents(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search the local indexed corpus with BM25 retrieval."""
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
        return [hit.to_dict() for hit in engine.search(query, top_k=top_k)]

    @server.tool()
    def ask_research_question(
        question: str,
        thread_id: str = "mcp-research-session",
        top_k: int = 5,
    ) -> str:
        """Run the stateful LangGraph workflow and return source-linked evidence."""
        result = ask_question(agent, question, thread_id=thread_id, top_k=top_k)
        return result["answer"]

    @server.tool()
    def get_source_document(doc_id: str) -> dict[str, Any]:
        """Return the exact indexed text chunk and metadata for a citation identifier."""
        document = engine.by_id.get(doc_id)
        if document is None:
            return {"error": "Document identifier not found", "doc_id": doc_id}
        return {
            "doc_id": document.doc_id,
            "text": document.text,
            "metadata": document.metadata,
        }

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hybrid RAG MCP server over stdio")
    parser.add_argument("--corpus", type=Path, default=Path("data/sample_corpus"))
    args = parser.parse_args()
    create_server(args.corpus).run(transport="stdio")


if __name__ == "__main__":
    main()
