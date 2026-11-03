from __future__ import annotations

import argparse
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from hybrid_rag.agent import ask_question, build_research_agent
from hybrid_rag.ingest import load_documents
from hybrid_rag.retrieval import SearchEngine


def create_server(
    corpus_dir: str | Path,
    *,
    dense: bool = False,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    rerank: bool = False,
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    chunk_size: int = 1800,
    chunk_overlap: int = 120,
) -> MCPServer:
    documents = load_documents(
        corpus_dir,
        chunk_size=chunk_size,
        overlap=chunk_overlap,
    )
    engine = SearchEngine(
        documents,
        embedding_model=embedding_model if dense else None,
        reranker_model=reranker_model if rerank else None,
    )
    agent = build_research_agent(engine)
    server = MCPServer("hybrid-rag-research")

    @server.tool()
    def search_documents(
        query: Annotated[str, Field(min_length=1, max_length=2000)],
        top_k: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, Any]]:
        """Search the local indexed corpus with BM25 and optional dense hybrid retrieval."""
        return [hit.to_dict() for hit in engine.search(query, top_k=top_k)]

    @server.tool()
    def ask_research_question(
        question: Annotated[str, Field(min_length=1, max_length=2000)],
        thread_id: Annotated[str, Field(min_length=1, max_length=128)] = "mcp-research-session",
        top_k: Annotated[int, Field(ge=1, le=20)] = 5,
        context_max_chars: Annotated[int, Field(ge=100, le=20000)] = 3000,
        context_max_chunks: Annotated[int, Field(ge=1, le=10)] = 5,
    ) -> str:
        """Run the stateful LangGraph workflow with bounded evidence context."""
        result = ask_question(
            agent,
            question,
            thread_id=thread_id,
            top_k=top_k,
            context_max_chars=context_max_chars,
            context_max_chunks=context_max_chunks,
        )
        return result["answer"]

    @server.tool()
    def get_source_document(
        doc_id: Annotated[str, Field(min_length=1, max_length=512)],
    ) -> dict[str, Any]:
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
    parser.add_argument("--dense", action="store_true", help="Enable SentenceTransformer embeddings")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--rerank", action="store_true", help="Enable cross-encoder reranking")
    parser.add_argument("--reranker-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    parser.add_argument("--chunk-size", type=int, default=1800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    args = parser.parse_args()
    create_server(
        args.corpus,
        dense=args.dense,
        embedding_model=args.embedding_model,
        rerank=args.rerank,
        reranker_model=args.reranker_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    ).run(transport="stdio")


if __name__ == "__main__":
    main()
