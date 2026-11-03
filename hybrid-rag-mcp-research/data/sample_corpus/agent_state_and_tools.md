# Stateful agent workflows and tool boundaries

A stateful agent workflow is a graph of explicit steps that exchange a typed state object. A graph can include retrieval, evidence extraction, critique, query rewriting, and synthesis. Conditional edges decide whether the workflow proceeds or loops back for another retrieval attempt.

Checkpointing associates graph state with a thread identifier. This supports resuming a workflow and inspecting previous steps within the lifetime and storage guarantees of the configured checkpointer. An in-memory checkpointer is convenient for local experiments but does not provide durable state across process restarts.

The Model Context Protocol (MCP) provides a standard interface for exposing tools and resources to compatible clients. A retrieval server can expose narrowly scoped tools such as search_documents, get_source_document, and ask_research_question. Each tool should validate inputs, limit result counts, return structured data, and avoid exposing local files outside the indexed corpus.

Tool execution should be least-privilege. Read-only tools are safer than tools that modify external systems. A tool should not execute arbitrary shell commands, accept unrestricted filesystem paths, or expose credentials. If write actions are introduced, they should require explicit authorization and audit logging.

A multi-step workflow is not automatically a multi-agent system. A prototype should clearly distinguish deterministic specialist nodes from independently prompted language-model agents. The orchestration graph, state transitions, retries, tool calls, and failure handling should be testable and observable.
