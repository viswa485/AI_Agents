# Metadata filtering and query preparation

Metadata filters constrain retrieval using trusted document attributes such as source, file type, tenant, product, date, or access scope. Apply access-control filters before returning results; do not rely on prompt instructions to enforce document permissions. A filter should use validated keys and values from an allowed schema.

Query normalization can clean whitespace, standardize known aliases, and preserve identifiers or technical tokens. Query rewriting can add context or alternative terms when a first retrieval attempt finds insufficient evidence. Rewriting should preserve named entities and important constraints rather than changing the user's intent.

Measure filtering and normalization changes against labelled examples. A filter that is too broad can expose irrelevant content; a filter that is too narrow can hide relevant documents.