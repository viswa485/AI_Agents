# Agent architecture and deterministic workflow boundaries

A multi-step graph is not automatically a multi-agent system. A deterministic graph may route state through specialist-named functions without calling any language model. An LLM-backed agent node uses a model to interpret context and produce a decision or action; separate nodes may use distinct prompts, model calls, tools, or policies.

Technical documentation should accurately distinguish deterministic orchestration, tool-using LLM agents, and independent specialist agents. Describe which components call a model, which components are rules or Python functions, and how each transition is tested.

Agent trajectory tests should cover the sequence of nodes, state updates, conditional routing, tool arguments, bounded retries, and error handling. A trace is useful for debugging but is not itself proof that an agent behaved correctly.