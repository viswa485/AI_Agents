# Hybrid RAG & Stateful MCP Research Prototype

A reproducible Python research project for hybrid retrieval, stateful LangGraph orchestration, MCP tool exposure, optional cross-encoder reranking, context budgeting, observability, and reference-based evaluation.

> **Scope and evidence boundary:** This is a research prototype, not a production customer deployment. The bundled corpus is synthetic technical documentation and the 50 labelled queries are a starter reference set. The dataset is not a representative external benchmark. The graph has deterministic offline fallbacks; when an OpenAI-compatible API key is configured, separate model calls are used for query rewriting, evidence critique, and synthesis. Do not describe offline fallback runs as LLM-backed multi-agent runs.

## What it implements

- Recursive Markdown/text ingestion, overlapping chunking, and stable source IDs.
- BM25 sparse retrieval.
- Optional Sentence Transformers dense embeddings.
- Weighted reciprocal-rank fusion for sparse/dense result lists.
- Optional cross-encoder candidate reranking.
- Metadata filtering and configurable top-K retrieval.
- LangGraph workflow with retrieval, evidence selection, critic, one rewrite loop, and synthesis.
- In-memory thread checkpointing using a caller-supplied thread ID.
- Optional LLM-backed query-rewriter, critic, and synthesis specialists through the OpenAI SDK.
- MCP stdio server with search, research-question, and exact source-chunk tools.
- Context pruning with an explicit character budget and token estimate.
- Optional Langfuse spans with input/output capture disabled by default.
- Reference-based Recall@K and MRR evaluation over a 50-query JSONL starter set.
- Automated tests and a GitHub Actions workflow.

## Architecture

~~~text
Markdown / TXT corpus
        |
        v
Ingestion + overlapping chunks + stable source IDs
        |
        +-------------------+
        |                   |
        v                   v
      BM25            Dense embeddings (optional)
        |                   |
        +--------+----------+
                 |
                 v
       Reciprocal-rank fusion
                 |
                 v
     Cross-encoder reranking (optional)
                 |
                 v
       LangGraph stateful workflow
      retrieval -> evidence -> critic
                |          |
                |       rewrite once
                |          |
                +<---------+
                 |
                 v
       context budget + synthesis
                 |
                 v
     answer with source identifiers

MCP tools: search_documents | ask_research_question | get_source_document
Observability: optional Langfuse spans, without prompt/output capture by default
Evaluation: labelled query -> relevant chunk IDs -> Recall@K / MRR
~~~

## Requirements and installation

- Python 3.11+
- Git
- Optional: model-capable CPU/GPU environment for Sentence Transformers models

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
~~~

Optional dependencies:

~~~bash
# Dense embeddings and cross-encoder reranking
python -m pip install -e ".[dense]"

# OpenAI-compatible LLM calls for separate rewrite, critic, and synthesis nodes
python -m pip install -e ".[llm]"

# Langfuse observability
python -m pip install -e ".[observability]"

# Install all optional runtime integrations and developer tools
python -m pip install -e ".[dev,dense,llm,observability]"
~~~

The first use of Sentence Transformers models may download model weights. The default BM25/offline path does not require an external model API.

To enable OpenAI-compatible calls, set environment variables locally:

~~~bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
# Optional for compatible providers:
# export OPENAI_BASE_URL="https://provider.example/v1"
~~~

To enable Langfuse, configure its project keys using the environment-variable names supported by your Langfuse deployment. Do not commit secrets. Trace decorators disable function argument and result capture by default; inspect your project-level privacy and retention settings before enabling broader capture.

## Run a BM25 search

Run commands from this project directory:

~~~bash
hybrid-rag --corpus data/sample_corpus search "How does reciprocal rank fusion combine rankings?"
~~~

Enable dense retrieval:

~~~bash
hybrid-rag --corpus data/sample_corpus --dense search "How does reciprocal rank fusion combine rankings?"
~~~

Enable dense retrieval and cross-encoder reranking:

~~~bash
hybrid-rag --corpus data/sample_corpus --dense --rerank search "How does reciprocal rank fusion combine rankings?"
~~~

The BM25-only mode is sparse retrieval. The hybrid sparse+dense path is enabled with the --dense option.

## Run the stateful workflow

~~~bash
hybrid-rag --corpus data/sample_corpus ask "How should I evaluate a hybrid RAG pipeline?" --thread-id demo-session
~~~

The workflow runs retrieval, evidence selection and a critic. When evidence is insufficient, it rewrites the query once and retries. It then produces a source-linked response. With OPENAI_API_KEY and the optional LLM dependency configured, query rewriting, critique, and synthesis use separate model calls. Without that configuration, deterministic local fallbacks run.

The default in-memory checkpointer keeps thread state only for the current process lifetime. It does not provide durable cross-restart persistence.

## Context budgeting

Retrieved chunks are pruned before synthesis using a configurable maximum number of chunks and character budget. A rough token estimate is reported as characters divided by four; this is a planning heuristic, not tokenizer-exact accounting. The intent is to constrain unnecessary context, not to claim a measured token-cost reduction.

## MCP server

~~~bash
hybrid-rag-mcp --corpus data/sample_corpus
~~~

The MCP server uses stdio and exposes:

| Tool | Purpose |
|---|---|
| search_documents | Retrieve source chunks from the indexed corpus |
| ask_research_question | Invoke the stateful LangGraph workflow |
| get_source_document | Return the exact indexed chunk for a source identifier |

The tools are read-only. They do not execute shell commands, access arbitrary caller-supplied file paths, or modify external systems.

Example client configuration (replace paths with absolute paths on your machine):

~~~json
{
  "mcpServers": {
    "hybrid-rag-research": {
      "command": "/absolute/path/to/.venv/bin/hybrid-rag-mcp",
      "args": ["--corpus", "/absolute/path/to/data/sample_corpus"]
    }
  }
}
~~~

## Run the 50-query retrieval evaluation

~~~bash
hybrid-rag --corpus data/sample_corpus evaluate --dataset data/eval_dataset.jsonl --k 5
~~~

The JSON output contains:

- query_count
- Recall@K
- Mean Reciprocal Rank (MRR)
- Per-query returned and relevant document identifiers

The starter set contains 50 labelled queries over the included synthetic corpus. It is useful for checking that the evaluation pipeline runs and for comparing code changes against the same fixed examples. It is not a representative production benchmark. Review and expand the labels before making general claims.

For a defensible experiment, record the corpus revision, chunk size/overlap, embedding model, candidate count, top-K, reranker, query set version, latency, and compute cost. Compare BM25-only, dense-only, hybrid, and hybrid-plus-reranker configurations on the same held-out queries.

## Tests and CI

~~~bash
pytest
ruff check src tests
~~~

The tests cover chunking, RRF, BM25 search, metadata filtering, evaluation metrics, context pruning, and the stateful workflow. GitHub Actions runs the tests and Ruff checks when the subproject changes.

## Limitations and roadmap

- The sample corpus is synthetic and deliberately small.
- The 50-query reference set is a starter set, not a customer dataset or independent benchmark.
- Dense retrieval and cross-encoder reranking are optional and depend on downloaded model weights.
- LLM-backed specialists require a configured API key and the optional OpenAI dependency.
- The deterministic fallback is not an LLM multi-agent system.
- Checkpointing is in-memory; configure a durable checkpointer before claiming restart persistence.
- The context token count is a rough character-based estimate.
- The prototype has not been load-tested or deployed as a production customer service.
- Future work: durable SQLite checkpointing, tokenizer-exact budgets, reviewed public-domain corpus, more rigorous retrieval/answer evaluation, citation validation, and deployment security controls.

## License

No separate licence is asserted for this subproject. Check the parent repository's licence and the licences of third-party dependencies before redistribution.
