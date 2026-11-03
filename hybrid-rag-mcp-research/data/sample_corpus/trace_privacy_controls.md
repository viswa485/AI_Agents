# Trace privacy and data minimization

Traces can expose user questions, retrieved passages, personal information, business data, and internal system details. Before enabling detailed tracing, classify the data, define retention, restrict access, and assess where the trace provider processes and stores information.

Prefer metadata and timing over raw prompt and output capture when content is not needed for debugging. Redact sensitive fields, avoid storing credentials, and use synthetic test data for development. Review both SDK settings and workspace-level retention or sampling policies.

Observability should support debugging without turning every user interaction into an unnecessary copy of sensitive application data.