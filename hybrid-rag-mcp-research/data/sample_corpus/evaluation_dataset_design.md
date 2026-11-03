# Reference evaluation dataset design

A reference dataset for retrieval evaluation should store each query and one or more reviewed relevant document or chunk identifiers. It should include typical requests, terminology variations, ambiguous wording, difficult examples, and queries for which no relevant evidence exists when abstention behavior is in scope.

Dataset size alone does not establish quality. Labels need review against the actual corpus, and the corpus revision and chunking configuration must be recorded. Keep tuning examples separate from a held-out evaluation set to reduce overfitting to the same queries.

A small synthetic dataset is useful for unit tests and smoke tests. It is not a representative customer benchmark and cannot support general claims about real-world answer quality. Expand and independently review the dataset before publishing performance claims.