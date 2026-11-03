# Model Context Protocol tool interfaces

The Model Context Protocol (MCP) defines a standard way for compatible clients to discover and invoke tools and resources exposed by a server. A retrieval MCP server can expose narrow tools such as search_documents, ask_research_question, and get_source_document.

Tool schemas should describe inputs and outputs clearly. Validate query lengths, result limits, identifiers, and optional settings at the tool boundary. Return structured results with stable source identifiers so clients can request the exact supporting passage.

MCP tools should have a narrow responsibility and bounded output. A search tool should not need arbitrary filesystem paths or unrestricted shell access. Read-only retrieval tools are easier to reason about than tools with external side effects.