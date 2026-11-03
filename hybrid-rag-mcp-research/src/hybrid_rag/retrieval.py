from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from hybrid_rag.models import Document, SearchHit
from hybrid_rag.observability import trace_span

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_+-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[int]],
    weights: Iterable[float] | None = None,
    rrf_k: int = 60,
) -> dict[int, float]:
    """Combine ranked document indexes with weighted reciprocal-rank fusion."""
    lists = list(ranked_lists)
    list_weights = list(weights) if weights is not None else [1.0] * len(lists)
    if len(list_weights) != len(lists):
        raise ValueError("weights must have the same length as ranked_lists")
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")

    fused: dict[int, float] = {}
    for ranked, weight in zip(lists, list_weights, strict=True):
        for rank, document_index in enumerate(ranked, start=1):
            fused[document_index] = fused.get(document_index, 0.0) + weight / (rrf_k + rank)
    return fused


class SearchEngine:
    """Local hybrid retriever with optional dense embeddings and cross-encoder reranking."""

    def __init__(
        self,
        documents: list[Document],
        *,
        embedding_model: str | None = None,
        reranker_model: str | None = None,
        rrf_k: int = 60,
    ) -> None:
        if not documents:
            raise ValueError("SearchEngine requires at least one document")
        self.documents = documents
        self.by_id = {document.doc_id: document for document in documents}
        if len(self.by_id) != len(documents):
            raise ValueError("Document identifiers must be unique")

        tokenized = [tokenize(document.text) or ["__empty__"] for document in documents]
        self._bm25 = BM25Okapi(tokenized)
        self._rrf_k = rrf_k
        self._embedding_model = None
        self._document_embeddings: np.ndarray | None = None
        self._cross_encoder = None

        if embedding_model:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Dense retrieval requires the optional dependency. Install with "
                    'pip install -e ".[dense]".'
                ) from exc
            self._embedding_model = SentenceTransformer(embedding_model)
            self._document_embeddings = np.asarray(
                self._embedding_model.encode(
                    [document.text for document in documents],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
            )

        if reranker_model:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "Cross-encoder reranking requires sentence-transformers. "
                    'Install with pip install -e ".[dense]".'
                ) from exc
            self._cross_encoder = CrossEncoder(reranker_model)

    @staticmethod
    def _matches_filters(document: Document, filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True
        return all(document.metadata.get(key) == value for key, value in filters.items())

    @trace_span("hybrid_rag.search")
    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: dict[str, Any] | None = None,
        candidate_k: int | None = None,
    ) -> list[SearchHit]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        eligible = [
            index for index, document in enumerate(self.documents)
            if self._matches_filters(document, filters)
        ]
        if not eligible:
            return []

        candidates = min(len(eligible), candidate_k or max(top_k * 4, 20))
        bm25_scores = np.asarray(self._bm25.get_scores(tokenize(query)), dtype=float)
        bm25_order = sorted(eligible, key=lambda i: bm25_scores[i], reverse=True)[:candidates]
        ranked_lists: list[list[int]] = [bm25_order]
        weights = [1.0]
        dense_order: list[int] = []

        if self._embedding_model is not None and self._document_embeddings is not None:
            query_embedding = np.asarray(
                self._embedding_model.encode(
                    [query],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
            )[0]
            dense_scores = self._document_embeddings @ query_embedding
            dense_order = sorted(eligible, key=lambda i: float(dense_scores[i]), reverse=True)[:candidates]
            ranked_lists.append(dense_order)
            weights.append(1.0)

        fused_scores = reciprocal_rank_fusion(ranked_lists, weights=weights, rrf_k=self._rrf_k)
        ordered = sorted(fused_scores, key=lambda index: fused_scores[index], reverse=True)[:candidates]
        bm25_ranks = {index: rank for rank, index in enumerate(bm25_order, start=1)}
        dense_ranks = {index: rank for rank, index in enumerate(dense_order, start=1)}

        hits = [
            SearchHit(
                doc_id=self.documents[index].doc_id,
                text=self.documents[index].text,
                metadata=self.documents[index].metadata,
                score=fused_scores[index],
                bm25_rank=bm25_ranks.get(index),
                dense_rank=dense_ranks.get(index),
            )
            for index in ordered
        ]

        if self._cross_encoder is not None and hits:
            pairs = [(query, hit.text) for hit in hits]
            scores = np.asarray(self._cross_encoder.predict(pairs), dtype=float).reshape(-1)
            hits = [
                SearchHit(
                    doc_id=hit.doc_id,
                    text=hit.text,
                    metadata=hit.metadata,
                    score=hit.score,
                    bm25_rank=hit.bm25_rank,
                    dense_rank=hit.dense_rank,
                    rerank_score=float(scores[index]),
                )
                for index, hit in enumerate(hits)
            ]
            hits.sort(
                key=lambda hit: hit.rerank_score if hit.rerank_score is not None else float("-inf"),
                reverse=True,
            )

        return hits[:top_k]
