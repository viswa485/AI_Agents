# Hybrid retrieval architecture

A retrieval-augmented generation system retrieves supporting passages before an answer is produced. A common pipeline normalizes a query, retrieves candidate passages, combines ranking signals, optionally reranks candidates, and passes a small evidence set to a downstream answer component.

Sparse retrieval such as BM25 is useful when a query includes exact terminology, identifiers, product names, or domain-specific phrases. Dense retrieval represents text as vectors and can retrieve semantically related passages even when the wording differs. Hybrid retrieval combines both result lists. Reciprocal-rank fusion is one method: each result receives a contribution inversely proportional to its rank in each ranked list.

Metadata filters can constrain retrieval by source, document type, tenant, date, or other trusted attributes. Filters should be applied before ranking results are returned. Cross-encoder rerankers score a query and candidate passage together and can improve ordering of a small candidate set, but they add latency and compute cost.

Evaluation should use labelled queries and relevant document identifiers. Recall@K measures the fraction of relevant documents found in the first K results. Mean reciprocal rank measures the reciprocal rank of the first relevant result. Evaluation sets should be representative, versioned, and kept separate from documents used to tune retrieval parameters.

A useful retrieval baseline records the corpus version, chunking configuration, embedding model, candidate count, reranker model, and metric definitions. A reported improvement is meaningful only when compared with a named baseline on the same labelled evaluation set.
