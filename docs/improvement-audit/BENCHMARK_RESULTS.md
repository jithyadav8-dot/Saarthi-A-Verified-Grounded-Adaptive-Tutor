# Controlled benchmark results

The improved system recovers more structured slide content, rejects the five targeted bad claim fixtures, and records each answered attempt once. Retrieval effectiveness was unchanged. With the ready-item filter enforced, the simulated adaptive arm exhausted its eligible pool sooner than the random arm.

| Metric | Original Saarthi | Improved Saarthi | Pramana (if comparable) |
|---|---:|---:|---|
| Retrieval hit@1 / hit@3 / MRR@3 | .95 / 1.00 / .975 | .95 / 1.00 / .975 | Not measured |
| Gold-unit precision@3 / recall@3 | .4667 / .9208 | .4667 / .9208 | Not measured |
| In-scope answered | 19/20 | 19/20 | Not measured |
| Off-topic refused / near-miss never fully grounded | 10/10 / 4/4 | 10/10 / 4/4 | Not measured |
| Gold citation location precision / answered with ≥1 correct location | .82 / 1.00 | .82 / 1.00 | Not measured |
| Faithfulness, answer relevancy, independent semantic citation support and natural model hallucination rate | Not measured | Not measured | Not measured |
| Scripted evidence contract, valid accepted / invalid rejected | 4/4 / 0/5 | 4/4 / 5/5 | Not measured |
| Scripted answer median latency | .0904 ms | .1525 ms | Not measured |
| Hosted inference latency | Not measured | Not measured | Not measured |
| Index build, traced Python allocation peak | 28.03 ms / 375,548 B | 28.40 ms / 375,548 B | Not measured |
| Retrieval median / p95 | 1.012 / 1.466 ms | .733 / 1.282 ms | Not measured |
| One native slide, probes recovered / extraction time | 1/7 / 15.50 ms | 7/7 / 16.90 ms | Not measured |
| Cold-start request 25, items returned / prerequisite violations | 25 / 14 | 11 / 0 | Not measured |
| Mastery first answer → exact retry / history entries | .7098 → .9292 / 2 | .7098 → .7098 / 1 | Not measured |
| Final simulated proficiency, adaptive / random | 39.4% / 39.5% | 38.1% / 39.5% | Not measured |
| Simulated questions answered, adaptive / random | 600 / 600 | 517 / 600 | Not measured |
| Paired difference in percentage points, 95% bootstrap interval | Not measured | −1.3487 [−1.8981, −.8305] | Not measured |
| Hosted inference calls / hosted tokens / provider spend | 0 / 0 / 0 | 0 / 0 / 0 | Not measured |

The Pramana column is reserved for measurements under the same conditions. Its published course, thresholds, models, simulator and evaluation labels differ. Its full suite could not collect locally because pypdfium2 was missing. The 27 successful reference tests establish behavior in the selected subset only. See [reference audit](PRAMANA_ARCHITECTURE.md).

## Workloads and interpretation

- **Retrieval.** All 20 bundled in-scope development queries against the same 28 units, with ten off-topic and four near-miss queries for answer behavior. Hash512 embeddings, lexical reranker, fixed corpus/graph, five timed searches per in-scope query. Hit@k credits any gold unit, MRR@3 the inverse rank of the first gold unit, precision@3 the fraction of the three that are gold, and recall@3 the fraction of labeled gold units found. These are unit-level metrics. RAGAS semantic context precision/recall require a separate run.
- **Ablation.** BM25 alone gave hit@1 .75, hit@3 .95, MRR@3 .85, precision@3 .3833 and recall@3 .8375. Hash dense alone gave .80, .90, .85, .3667 and .8250 respectively. The existing hybrid also reranks and boosts named concept evidence. The observed difference cannot be attributed solely to RRF. Timing differences across runs are consistent with local noise. Tracemalloc excludes native allocations and total process RSS.
- **Grounding.** Nine authored cases include literal support, paraphrase, a valid number, valid quote, changed number, added/removed negation, fabricated quote and irrelevant quote. A scripted generator supplies fixed payloads with one source per case, zero retrieval gate thresholds and seven repeats. This isolates the acceptance contract. The same four valid answers survived, and five false acceptances became refusals. Source-location precision can credit an incorrect assertion that cites the right page.
- **Ingestion and grading.** One synthetic deck exercises native content and one learner receives one correct answer twice. Extraction timing is a single observation. Question key quality, item difficulty calibration, unseen-course semantic duplication, diagram OCR, realistic concurrency throughput and production error rate are **Not measured**. Rollback, source viewing, diagnostic behavior and parallel retries have targeted regression coverage.
- **Adaptive learning.** 30 simulated students, eight concepts, five sessions, four requested questions per session, seed 42. Initial synthetic proficiency is uniform [.15,.45]. Response chance is .2 + .7p. A correct response raises proficiency by .08(1−p) and an incorrect response by .04(1−p). Both arms use the same learning rule. Difficulty and forgetting are absent. The revised interval resamples paired final outcomes by student 2,000 times. Its scope is variation under this simulator. Unequal exposure confounds a policy effect per question. Real learner outcomes and mastery calibration are **Not measured**.
- **Configuration.** Windows, Python 3.12.10, Node 25.8.0 and existing installed packages. No model weights or remote inference. Prompts are source-versioned in `src/retrieval/answer.py`. Scripted payloads bypass model generation, so changing prompts cannot be evaluated here. Baseline source is commit `42b0b63cf0e8334597ff53d00b91995fe962cc73`. Improved source is the delivered branch working tree. Results include locally observed timings, not latency guarantees.

## Reproduction on Windows

From the repository root, install dependencies and set the offline variables in the [README](../../README.md). Use a fresh directory for baseline extraction. Both runs below use the *current harness* with different source roots. Use the same Python environment for both.

```powershell
New-Item -ItemType Directory -Force .audit_tmp | Out-Null
git archive --format=zip --output=.audit_tmp/baseline-repro.zip 42b0b63cf0e8334597ff53d00b91995fe962cc73
Expand-Archive .audit_tmp/baseline-repro.zip .audit_tmp/baseline-repro
py -3.12 scripts/benchmark_improvements.py --source-root .audit_tmp/baseline-repro --output .audit_tmp/before.json
py -3.12 scripts/benchmark_improvements.py --source-root . --output .audit_tmp/after.json
py -3.12 -m scripts.benchmark_grounding_contract --output .audit_tmp/claims-after.json
Copy-Item scripts/benchmark_grounding_contract.py .audit_tmp/baseline-repro/scripts/
Push-Location .audit_tmp/baseline-repro
try { py -3.12 -m scripts.benchmark_grounding_contract --output ../claims-before.json } finally { Pop-Location }
py -3.12 scripts/eval_grounding.py
```

Original run records: [controlled before](controlled-before.json), [controlled after](controlled-after.json), [claim cases before](grounding-contract-before.json), [claim cases after](grounding-contract-after.json). Protocol identifiers inside the JSON distinguish the two workloads. Relative timing changes are descriptive. The fixture authors knew the product, so these tests should remain regressions and a separate held-out set should be used for accuracy claims.
