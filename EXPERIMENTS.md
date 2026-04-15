# Experiments Log

## Baseline (Dense Retrieval Only)
- Retrieval stack: FAISS dense search only
- Recall@5: <FILL_ME>
- MRR: <FILL_ME>
- Observed issue: misses exact-author queries and acronym-heavy prompts

## Improvement 1 (Hybrid Dense + BM25)
- Retrieval stack: FAISS + BM25 with RRF fusion
- Recall@5: <FILL_ME>
- MRR: <FILL_ME>
- Delta vs baseline: <FILL_ME>
- Outcome: stronger exact-term recovery without losing semantic coverage

## Improvement 2 (Prompt and Guardrail Tuning)
- Generation changes: strict grounding prompt + out-of-scope policy + natural citations
- Groundedness: <FILL_ME>
- Hallucination rate: <FILL_ME>
- Avg latency: <FILL_ME>
- Outcome: better trust signals and safer out-of-domain behavior

## Failure Analysis (Top 5 Ongoing Fails)
1. Query: <FILL_ME>
   - Failure mode: <FILL_ME>
   - Root cause: <FILL_ME>
   - Planned fix: <FILL_ME>
2. Query: <FILL_ME>
   - Failure mode: <FILL_ME>
   - Root cause: <FILL_ME>
   - Planned fix: <FILL_ME>
3. Query: <FILL_ME>
   - Failure mode: <FILL_ME>
   - Root cause: <FILL_ME>
   - Planned fix: <FILL_ME>
4. Query: <FILL_ME>
   - Failure mode: <FILL_ME>
   - Root cause: <FILL_ME>
   - Planned fix: <FILL_ME>
5. Query: <FILL_ME>
   - Failure mode: <FILL_ME>
   - Root cause: <FILL_ME>
   - Planned fix: <FILL_ME>

## Lessons Learned
- Retrieval quality drives generation quality more than model size alone.
- Metadata fidelity (`book`, `page`, `chunk_id`) is critical for trust and debugging.
- Out-of-scope behavior must be explicit and tested; default LLM behavior is too permissive.
- Evaluation harnesses reveal regressions that demos hide.
