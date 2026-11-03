# LLM observability and agent trajectories

Useful workflow spans include query normalization, retrieval, reranking, context pruning, model invocation, tool execution, critique, and synthesis. Trace parent-child relationships make it possible to inspect the sequence of operations and where time or failures occurred.

Operational signals include request latency, model latency, provider and model name, input/output token usage, retry count, tool error rate, retrieval count, and evaluation outcome. Compare token usage and latency alongside retrieval and answer quality rather than optimizing one metric in isolation.

A trace helps diagnose a run but should not automatically store full user prompts or retrieved documents. Capture only necessary metadata, and document what is recorded and for how long.