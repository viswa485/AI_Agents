# Rank fusion and reranking

Reciprocal-rank fusion combines multiple ranked lists using a contribution based on the reciprocal of each document's rank, often with a configurable smoothing constant. It avoids requiring BM25 and embedding similarity scores to share the same numeric scale. Weights can be applied when one retrieval channel should contribute more strongly.

A cross-encoder reranker takes a query and a candidate passage together and predicts a relevance score. A common pattern is to retrieve a larger candidate set using sparse and dense search, fuse the rankings, and rerank only the top candidates. This can improve ordering at the cost of additional inference time and compute.

Reranking should be compared with the same candidate set and labelled queries as the unre-ranked baseline. Record the candidate count, model, latency, and evaluation metrics to understand the quality-cost trade-off.