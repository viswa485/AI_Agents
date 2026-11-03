# Answer faithfulness and citation review

Answer faithfulness asks whether each factual claim in a generated answer is supported by the retrieved context. It is different from retrieval recall: a system can retrieve the right passage and still produce an incorrect or unsupported answer.

A human reviewer should compare each answer sentence with the corresponding evidence passage and source document. Check whether claims are entailed by the evidence, whether citations point to the passages that support the claims, whether important context was omitted, and whether the system should have abstained.

Citation presence or an LLM critic's self-assessment is not proof of faithfulness. Keep answer-quality review separate from retrieval metrics, record unsupported claims and citation errors, and use the findings to improve prompts, retrieval, and evaluation examples.