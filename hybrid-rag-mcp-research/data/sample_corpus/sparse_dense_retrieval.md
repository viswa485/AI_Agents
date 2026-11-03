# Sparse and dense retrieval

BM25 is a sparse lexical ranking method that scores documents using term frequency, inverse document frequency, and document-length normalization. It is effective when users include exact technical terms, identifiers, names, or uncommon tokens that also appear in the corpus. It can miss semantically related passages when the query and source use different words.

Dense retrieval encodes queries and passages into vector embeddings. Similarity between the vectors can retrieve semantically related text even when exact terms do not overlap. Dense retrieval depends on the embedding model, text domain, normalization, and vector index configuration.

Hybrid retrieval combines sparse BM25 results and dense vector results. A fusion stage combines ranked lists so exact lexical matches and semantic matches can both contribute. The BM25-only configuration is a useful baseline; the hybrid configuration should be evaluated on the same labelled query set before concluding that it is better.