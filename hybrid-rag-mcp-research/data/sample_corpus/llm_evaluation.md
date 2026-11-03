# LLM evaluation and observability

LLM application evaluation should measure retrieval quality and answer quality separately. Retrieval evaluation can use Recall@K and mean reciprocal rank on a labelled query set. Answer evaluation may inspect faithfulness to retrieved context, answer relevance, citation correctness, refusal behavior, and structured-output validity.

A reference dataset should record each query and one or more relevant source identifiers. Dataset size alone does not establish quality. The labels need review, examples should reflect likely user questions, and the dataset should include difficult or ambiguous cases. Metrics should be reported with the exact corpus and configuration used.

Tracing can record workflow spans such as query normalization, retrieval, reranking, model invocation, and tool execution. Useful operational signals include latency, token usage, failure rate, retry count, and model/provider choice. Traces may contain sensitive queries or retrieved documents, so applications should minimize captured content, redact personal data, define retention, and restrict access.

A regression gate can compare a candidate build with a baseline and flag a meaningful drop in a selected metric. Thresholds should be set from observed variance and product requirements rather than chosen arbitrarily. Evaluation results are evidence about the tested dataset, not a guarantee of performance on unseen queries.
