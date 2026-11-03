# Regression gates and controlled experiments

An evaluation regression gate compares a candidate build with a known baseline and flags a meaningful change in selected metrics. Thresholds should reflect measurement noise, dataset size, product requirements, and the cost of false alarms. Avoid selecting thresholds solely because they make a test pass.

For each experiment, tie results to the corpus version, query-set version, chunking settings, embedding model, candidate count, reranker, prompt version, and runtime environment. Keep prompt or chunking changes isolated when possible so the reason for a metric change can be understood.

Retrieval metrics do not guarantee answer faithfulness or usefulness. Review answer claims and citations against evidence, record latency and token use, and inspect per-query regressions. Small synthetic datasets are suitable for software checks, not general claims about production users.