# Stateful graph workflows

A stateful agent workflow represents a task as a graph whose nodes read and update a typed state object. Nodes can represent retrieval, evidence extraction, critique, query rewriting, tool execution, and synthesis. Explicit edges define the normal sequence, while conditional edges select a branch based on the current state.

A critic can route a workflow to a query rewrite when retrieved evidence is insufficient. A bounded retry count prevents uncontrolled loops. The graph should preserve the original user question separately from rewritten retrieval queries so the final answer remains aligned with the original intent.

Graph state and node boundaries make agent trajectories inspectable. Tests can verify expected transitions, retry limits, state updates, and failure behavior without assuming that every node is a separate autonomous language-model agent.