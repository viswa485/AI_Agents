# Retrieval metrics and experimental baselines

Recall at K measures how many of the labelled relevant documents appear in the first K retrieved results, divided by the number of relevant documents for that query. Mean reciprocal rank (MRR) is the average reciprocal rank of the first relevant result. Both metrics require a query set with reviewed relevant document identifiers.

A useful retrieval baseline records the corpus revision, parser, chunk size, chunk overlap, embedding model, sparse tokenizer, candidate count, fusion weights, reranker model, and top-K. Candidate count and reranker choice influence both relevance ordering and runtime. Keep the query set fixed when comparing BM25-only, dense-only, hybrid, and hybrid-plus-reranker configurations.

Report metrics with the dataset version and confidence limitations. A measurement on one corpus and query set does not establish performance on another corpus or unseen user questions. Include per-query failures rather than only a single aggregate score.