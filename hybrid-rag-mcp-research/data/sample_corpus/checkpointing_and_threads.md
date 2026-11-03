# Checkpointing and thread state

A LangGraph checkpointer saves workflow state under a thread identifier. Reusing a thread ID allows the workflow to continue from previously checkpointed state, subject to the checkpointer's storage and retention behavior. A new thread ID creates an isolated conversation or task history.

An in-memory checkpointer is useful for local development and tests, but its state is lost when the process exits. Durable checkpointing requires a persistent backend, such as a supported SQLite or database checkpointer, plus a defined retention and cleanup policy.

Checkpoint/resume behavior should be tested by interrupting or ending a workflow, reusing the thread ID, and confirming the intended state is restored. Do not call an in-memory checkpointer durable across process restarts.