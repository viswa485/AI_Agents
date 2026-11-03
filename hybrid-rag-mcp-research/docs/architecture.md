# Architecture and implementation boundaries

## Components

1. **Ingestion** reads Markdown and text documents, chunks them with overlap, and assigns stable source identifiers.
2. **Sparse retrieval** uses BM25 over tokenized chunks.
3. **Dense retrieval** is an optional Sentence Transformers adapter.
4. **Hybrid fusion** combines sparse and dense rankings with weighted reciprocal-rank fusion.
5. **Reranking** is an optional cross-encoder pass over the fused candidate set.
6. **LangGraph workflow** runs retrieval, evidence extraction, a critic, one query-rewrite retry, and extractive or optional LLM synthesis.
7. **MCP server** exposes search, source lookup, and research-question tools over stdio.
8. **Evaluation** calculates Recall@K and MRR against a JSONL file containing labelled relevant document identifiers.
9. **Observability** applies an optional Langfuse decorator when the SDK is installed.

## Stateful execution

The graph uses LangGraph's in-memory checkpointer and accepts a caller-provided thread ID. This supports checkpointed state during the process lifetime. The default in-memory checkpointer is not durable across restarts. Install and configure a persistent checkpointer before describing the system as durable.

## Agent boundary

When OPENAI_API_KEY is configured and the optional OpenAI SDK is installed, query rewriting, evidence critique, and synthesis use separate specialist model calls. Without that configuration, local deterministic fallbacks run. Do not describe the offline fallback as LLM-powered multi-agent execution.

## Data and security boundaries

Only Markdown and text files under the selected corpus directory are indexed. MCP tools do not accept arbitrary filesystem paths or run shell commands. The sample corpus is synthetic technical material and is not a real customer knowledge base.

## Performance and evaluation

The included labelled dataset is a smoke-test dataset. It is too small to support a general performance claim. Run evaluation against a representative, reviewed dataset before reporting Recall@K, MRR, faithfulness, latency, or cost. Record model names, corpus revision, chunking settings, top-K, candidate count, and reranker configuration with each experiment.
