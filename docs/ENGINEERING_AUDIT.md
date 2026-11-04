# Saarthi engineering audit — 2026-11-03–05

## Outcome and limits

This audit implemented local corrections to grading, uploads, evidence reporting, provider failure handling, learner persistence, quiz selection, evaluation validity, frontend integration, and vulnerable frontend dependencies. Each accepted change has either a reproduced failing case or a concrete source/dependency baseline, followed by checks of the changed behavior. No hosted models, production data, external infrastructure, commits, or pushes were used.

The project is still a **local, single-process demonstration**. This report does not certify production readiness or improved educational effectiveness. The corrected simulation produced **39.4% adaptive versus 39.5% random final mastery**, with 600 questions in each arm. That is no evidence of an adaptive-learning advantage. Real learner outcomes, hosted-model accuracy, RAGAS metrics, full multimodal ingestion quality, and end-to-end performance remain **Not measured**.

## Discovery and baseline

- Checkout: nested source directory inside the supplied Downloads workspace; neither directory contains Git metadata. Remote synchronization, a clean-tree comparison, and commit-level provenance were unavailable. Existing work was retained; no repository was initialized or reset.
- Primary entry point: `src.api.service:app`; Next.js App Router in `src/ui`; alternate ingestion services in `src/ingestion/main.py` and `backend/app/main.py`.
- Main flow: upload/parsers → ingestion ContentUnits → adapter → live corpus/hybrid retriever → claim-checked answerer → HTTP/chat SQLite. Assessment uses a separate **bundled curated** concept/question bank, BKT updates, and adaptive selection. Uploads do not automatically replace the assessment curriculum.
- Retrieval uses BM25 + dense fusion + reranking and a refusal gate. Offline checks selected hashing embeddings, lexical reranking, and no LLM. Graph building and enriched media pipelines can call providers and were inspected but not executed against them.
- Ingestion duplication: 62 backend Python files matched their `src/ingestion` counterparts after namespace normalization. The checkpoint package was missing in the latter. Mirrored safety fixes retain both supported entry points; wholesale consolidation was deferred.
- Environment: Windows, Python 3.12.10, Node 25.8.0, npm 11.11.0. Python packages were already installed; the frontend initially lacked `node_modules` and its entire imported `lib` directory.
- Existing Python tests initially hung in Windows `asyncio` socket-pair creation under the sandbox. A traceback identified an environment restriction, before application request handling. Running outside that restriction worked. An early run then had 105 passes and 23 temporary-directory setup errors; these are not application failures. Later combined runs exercised all 128 existing tests.
- Eight new learning/evaluation tests failed before their fixes. Nine initial unified-service tests produced eight failures and one pass. A separate persistence test reproduced mastery dropping from 0.7098 to 0.3000 after clearing in-memory state.
- `pip check` reported an existing environment conflict: installed Streamlit requires pyarrow <26, while the environment has pyarrow 26. Streamlit is not in this project's root manifest; the shared Python environment was not modified.
- Broad Ruff output initially reported 442 issues under inherited configuration, mostly imports, annotation modernization, and broad exception handlers. No project Python lint/type configuration was present. This was not used as justification for mass formatting.
- Frontend baseline: missing source modules prevented compilation; initial lint/build also lacked installed tools. Restoring adapters exposed 18 TypeScript diagnostics, subsequently resolved. The first production build could not download Google fonts inside the sandbox; the same build succeeded with permitted network access.

## Prioritization and hypothesis inventory

Severity takes precedence: P0 security/critical integrity, P1 significant functional/reliability failure, P2 maintainability or bounded efficiency. Within severity, score = impact × confidence / (effort × regression risk). Impact is 1–5; confidence, effort and risk are 1–3. Scores are triage aids, not measurements of benefit.

| ID | Priority | Component | Existing behavior / evidence | Smallest change and expected benefit | I/C/E/R; score | Validation / result |
|---|---|---|---|---|---|---|
| A01 | P0 | unified and both ingestion upload APIs | Raw filenames could escape uploads; Windows preview paths could read outside it; unbounded copies | Portable basename validation, contained paths, bounded temporary-file write and atomic replacement; reject bad input before writing | 5/3/2/2; 3.75 | Traversal, oversize preservation, cleanup, preview and real TXT roundtrip tests pass |
| A02 | P0 | frontend dependencies | npm audit: 2 critical, 3 high, 18 moderate package findings | Next 16.4.0→16.4.4, matching eslint config; PDF.js 3.11→6.5.438; compatible Zod patch | 5/3/2/2; 3.75 | Rebuild/typecheck pass; rescan 0 critical, 0 high, 16 moderate, all remaining in dev dependencies |
| A03 | P1 | assessment verifier | Empty answer, `incorrect`/`correct`, `not increasing`/`increasing`, `5`/`15` accepted; `1e3` treated as 3 | Compare complete normalized text; parse full finite decimals/scientific notation; no dry-run verification certification | 5/3/1/2; 7.5 | Rejection and valid-format regressions pass; semantic paraphrases deliberately require a future grounded judge |
| A04 | P1 | SymPy checker | `__import__('builtins').len([1,2,3])` evaluated to 3 | Construct allowlisted arithmetic/function AST directly; bound syntax, derivative order and integer powers; reject arbitrary Python | 4/3/2/2; 3 | Unsafe expressions and substitutions rejected; documented derivative/arithmetic examples preserved |
| A05 | P1 | `src/ui/lib`, build setup | Required adapters, types and PDF-thumbnail module absent; generic `lib/` ignore excluded source | Restore typed API contracts and local PDF preview; ensure matching worker copied on dev/build; narrow source ignore exceptions | 5/3/3/2; 2.5 | Typecheck and all six production routes build; fresh install reproducibility still relies on registry/font access |
| A06 | P1 | upload/quiz/evaluation UI | Backend errors fabricated indexed units or correct grades; numeric type fabricated math verification; benchmark fallback invented scores | Propagate API errors, keep failed answer retryable, render actual upload samples, explicit unavailable states and provenance | 5/3/2/1; 7.5 | Six API-contract tests plus twelve UI render/callback checks pass; frontend compiles; full browser interaction coverage remains outstanding |
| A07 | P1 | unified evidence and source endpoints | Missing units returned invented excerpts; substring matching could attach wrong evidence; `/sources` links had no unified route | Exact evidence lookup/404, show only existing evidence, safe source alias and URL-encoded filenames | 5/3/1/2; 7.5 | Unknown/real evidence and encoded citation/source tests pass |
| A08 | P1 | learner state / SQLite | Mastery and feedback disappeared on restart although quiz history remained | Additive `learner_profiles` table; restore BKT/history, serialize answer updates, rollback memory if persistence fails | 5/3/2/2; 3.75 | Mastery/history survive memory reset; synthetic disk failure gives 503 without changing mastery |
| A09 | P1 | adaptive selection | Two-question pool filled five slots with repeats; unknown target silently used unrelated topics; used IDs reused | Stop at unique eligible pool exhaustion, honor target filtering, reject unknown API concept; reset prior-use cycle only when empty | 4/3/1/2; 6 | Exhaustion, target, prior-use and API regressions pass; shorter quizzes are now explicit behavior |
| A10 | P1 | diagnostic endpoint | Accessed nonexistent `LearnerModel._p`; would also fabricate priors without student answers | Return real diagnostic questions and `diagnostic_ready`; no prior changes until answers | 4/3/1/1; 12 | No exception; questions omit answer keys; mastery remains unchanged |
| A11 | P1 | answerer | Transport failures and malformed model fields escaped; unsupported text returned despite opt-out | Validate response shapes, catch transport failures, degrade to cited excerpts, honor outside-knowledge opt-in | 4/3/2/2; 3 | Timeout/connect/malformed/followup/opt-in regressions pass; no live-model quality claim |
| A12 | P1 | ingestion initialization/checkpoints | Light imports loaded model pipelines; `src.ingestion.checkpoints` absent | Lazy package exports; restore checkpoint implementation already present in backend | 4/3/1/1; 12 | Light imports and checkpoint roundtrip pass without provider calls; complete enriched pipeline remains unmeasured |
| A13 | P1 | both Qdrant services | Any persistent-store error silently opened ephemeral memory storage | Fail explicitly and close an opened client on initialization failure | 4/3/1/2; 6 | Simulated locked database produces one open attempt and explicit failure, no in-memory fallback |
| A14 | P1 | ablation / RAGAS reporting | Adaptive arm got 0.12/0.04 learning gain versus random 0.08/0; hardcoded p-value and RAGAS scores | Same 0.08/0.04 rule, paired response seeds, distinct selection RNG, equal finite pools, bounded inputs; null unmeasured statistics | 5/3/2/1; 7.5 | Identical one-question policies yield identical curves; default arms each ask 600 questions; no adaptive benefit established |
| A15 | P2 | both chunkers | Exactly 1,200 characters generated a redundant 200-character trailing chunk | Stop when final character is covered; validate size/overlap | 3/3/1/1; 9 | Exact-boundary tests: 2→1 chunks, 1,400→1,200 indexed characters; repeated microbenchmark below |
| A16 | P2 | chat UI | Late load/send responses could overwrite the newly selected session | Invalidate outstanding view requests on switch/new chat/send, ignore stale completions | 3/3/1/2; 4.5 | Source review and TypeScript/build validation; race interaction has not been browser-automated |
| A17 | P1 | unified API limits | Native retrieval protections were bypassed by integration chat/upload routes; unrestricted benchmark workload | Reuse existing chat limiter/admin-token guard, bound queries/workload, honor configured CORS, move blocking upload to FastAPI worker thread | 4/3/1/2; 6 | Chat rate-limit and workload regressions pass; this does not provide user authentication |
| A18 | P1 | runtime and graph persistence | Failed persistence exposed a new bundle; partial writes corrupted the graph file; rejected uploads changed live concepts and replacements retained stale evidence | Persist before publishing; atomically replace the graph file; merge upload graph additions into the private copy under the ingestion lock | 5/3/2/2; 3.75 | Five reproduced failures now pass; cross-file crash consistency and uploaded-file rollback still need a transaction design |
| A19 | P1 | image and media integration | Upload/startup imported nonexistent `describe_image`; missing Groq key blocked importing pipelines unrelated to transcription | Use the actual image-caption function; initialize the transcription provider only when needed | 4/3/1/2; 6 | Isolated integration/import checks; no real image-caption or transcription quality claim |
| A20 | P1 | graph and citation UI | Empty evidence fallback crashed; mastery and a perfect faithfulness score were fabricated; consecutive nodes implied nonexistent prerequisite edges | Render unavailable/unknown states, load actual learner values, and show only actual prerequisite connectors | 5/3/2/1; 7.5 | Render regressions cover missing evidence, unknown mastery and unsupported certification |
| A21 | P1 | chat and quiz failure states | Failed chat loading/deletion left busy state; failed creation fabricated a session; empty quiz response retained old questions | Finish loading in `finally`, display retryable errors, clear deleted selection and replace the quiz even when empty | 4/3/1/2; 6 | Source baseline plus callback/render checks and TypeScript/build validation; browser coverage remains outstanding |

### Implementation and test map

Paths below are relative to the nested repository root. Mirrored ingestion changes were applied to both supported trees.

| Hypotheses | Main changed files | Focused verification |
|---|---|---|
| A01, A07, A17 | `src/ingestion/upload_safety.py`, `backend/app/upload_safety.py`, both ingestion `api/knowledge.py` files, `src/api/service.py`, `src/retrieval/schemas.py` | `tests/test_ingestion_safety.py`, `tests/test_service_reliability.py` |
| A02, A05 | `src/ui/package.json`, `package-lock.json`, `lib/api.ts`, `lib/mockData.ts`, `lib/generatePdfThumbnail.ts`, `scripts/copy-pdf-worker.mjs`, `.gitignore` | Dependency rescan, TypeScript and production build |
| A03, A04 | `src/assessment/verifier.py`, `src/assessment/sympy_check.py` | `tests/test_assessment_safety.py` |
| A06 | `src/ui/components/CourseUploadModal.tsx`, `LearnerModelArena.tsx`, `EvaluationResults.tsx`, `EvaluationAblationModal.tsx`, `src/ui/app/quiz/page.tsx`, `app/benchmark/page.tsx`, `lib/api.ts` | `src/ui/scripts/api.test.mjs`, `ui-callbacks.test.mjs`, `ui-render.test.mjs`, build |
| A08, A10 | `src/api/service.py` | Learner restart, persistence rollback and diagnostic cases in `tests/test_service_reliability.py` |
| A09, A14 | `src/learner_model/adaptive.py`, `live_course_data.py`, `src/api/service.py` | `tests/test_learning_reliability.py`, service regressions, paired simulation |
| A11 | `src/retrieval/answer.py`, `src/retrieval/llm.py` | `tests/test_grounding_failures.py`, existing `test_step3.py` and `test_step4.py` |
| A12, A13, A15 | `src/ingestion/__init__.py`, `src/ingestion/checkpoints/`, both `vectorstore/qdrant_service.py` and `processing/chunker.py` mirrors | `tests/test_ingestion_safety.py`, `scripts/benchmark_chunking.py` |
| A16 | `src/ui/app/chat/page.tsx` | Source review, TypeScript and build; no automated browser race test |
| A18 | `src/retrieval/runtime.py`, `src/graph/graph.py`, `src/api/service.py` | `tests/test_runtime_persistence.py`, `tests/test_upload_graph_atomicity.py`, existing concurrent/restart cases in `test_step5.py` |
| A19 | `src/api/service.py`, both `ingestion/video_transcriber.py` mirrors | `tests/test_image_upload_integration.py`, `tests/test_video_transcriber_lifecycle.py` |
| A20, A21 | `src/ui/app/graph/page.tsx`, `app/quiz/page.tsx`, `app/chat/page.tsx`, `components/PrerequisiteGraph.tsx`, `CitationDrawer.tsx`, `ChatSidebar.tsx`, `lib/mockData.ts` | Eight server-render tests and four callback tests |
| Documentation and reproducibility | `README.md`, `.env.example`, `.gitignore`, `scripts/smoke_offline.py`, this report and `audit_evidence.json` | Documented commands, real-process startup smoke and evidence consistency check |

## Before and after evidence

| Measurement | Before | After | Interpretation |
|---|---|---|---|
| New learning/evaluation regression cases | 8 failed / 0 passed | 8 passed | Concrete selection and experiment-validity defects corrected |
| Initial unified-service regression cases | 8 failed / 1 passed | All corrected cases pass | The Windows absolute-filename case was refined: multipart normalizes it to a safe basename; direct helper rejects raw absolute paths |
| Mastery after memory reset | 0.3000 instead of 0.7098 | Restored 0.7098 | Local persistence verified |
| npm critical / high / moderate package findings | 2 / 3 / 18 | 0 / 0 / 16 | Remaining 16 are development-tool dependencies, not a claim of zero vulnerability |
| TypeScript after missing-module restoration | 18 diagnostics | 0 | Includes PDF.js API migration fixes |
| Frontend production build | Missing source/deps; later font-network failure | Pass, 8 static pages generated (6 application routes) | Not a latency benchmark |
| 1,200-character document chunks / indexed characters | 2 / 1,400 | 1 / 1,200 | Removes a redundant overlap chunk without dropping source characters |
| Chunking 1,000 such documents, median of 7 repeats | 1.0612 ms | 0.8162 ms | Tiny synthetic microbenchmark only; timing ranges overlap, so no general speedup claim |
| Identical one-question simulation policies | Different curves | Identical curves | Experimental bias removed |
| Runtime publication / graph partial-write regressions | 2 failed | 2 passed | Failed writes preserve the prior visible bundle and prior graph file |
| Upload graph failure/replacement regressions | 3 failed | 3 passed | Rejected uploads preserve live graph state; successful replacements refresh evidence |
| Image integration / transcription lifecycle regressions | 7 failed | 7 passed | Correct callable integration and optional provider initialization |
| Rational-power / raw-provider-response regressions | 12 failed, 2 valid controls passed | 14 passed | Extends the first fix to reciprocal powers and actual malformed HTTP responses |

The bundled offline grounding evaluation was rerun with `hash:512|lexical`: hit@1 0.95, hit@3 1.00, strict precision@3 0.47, 19/20 in-scope questions answered, citation precision 0.82, 10/10 off-topic refusals, 4/4 near-misses not confidently grounded. These match the repository's recorded development baseline. This is **regression preservation**, not a demonstrated improvement in retrieval quality. The small corpus and query set share an author and do not establish generalization.

## Reproduction and verification

Final results: **229 Python tests passed, 0 failed, 0 skipped** (128 existing cases plus 101 added); **18 frontend tests passed, 0 failed**. Standalone TypeScript, the Next.js production build, the real offline server smoke test and focused Python fatal-error checks passed. The frontend build generated eight static pages across six routes. Test durations are recorded for reproducibility, not treated as an application performance benchmark.

```powershell
# Repository root; no hosted models required
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:EMBEDDING_PROVIDER = "hash"
$env:RERANK_PROVIDER = "lexical"
$env:LLM_PROVIDER = "none"
$env:POD_B_ENV_FILE = ".audit_tmp/nonexistent.env"
python -m pytest tests -q
python -m scripts.smoke_offline
python -m scripts.benchmark_chunking
python -m ruff check --isolated --select E9,F63,F7,F82 src backend/app scripts tests

# Explicitly offline retrieval evaluation
$env:EMBEDDING_PROVIDER = "hash"
$env:RERANK_PROVIDER = "lexical"
$env:LLM_PROVIDER = "none"
python scripts/eval_grounding.py

cd src/ui
npm ci
npm test
npm run typecheck
npm run build
npm run lint
npm audit
```

The offline regression suite uses real FastAPI TestClient routes and temporary local storage; remote-model responses and database failure conditions are faked. The real-process smoke test starts Uvicorn on an ephemeral loopback port, checks health/quiz/evaluation, terminates it, and removes its temporary state. Node tests exercise the actual TypeScript API adapter after transpilation, including failed uploads/grading and preservation of server evidence. UI tests render actual components on the server or invoke their callbacks with controlled hooks and API promises. They do not model browser layout, React scheduling or DOM event propagation.

**Lint is not clean.** The final frontend lint run reports 21 errors and 34 warnings, primarily existing `any` types, hook/render rules and JSX escaping. Generated PDF.js worker code is excluded from source lint. Focused Python fatal-error checks pass. Broad Python modernization and a full mypy run were not completed. No comprehensive browser-driven end-to-end test was executed.

## Second-pass review and outstanding work

The specialist reviews covered ingestion/storage, retrieval/assessment, and frontend contracts. After an interruption, the specialists resumed and challenged the implemented changes. Their second pass found further reproducible failures in image integration, raw provider-response handling, rational-power bounds, graph evidence and UI claims. The coordinating engineer additionally tested persistence failure and reviewed chat/quiz error paths. This is an internal second review by the same engineering team, not an independent security certification.

Second-pass corrections included: bounding reciprocal/rational powers, normalizing malformed provider responses into the existing fallback, making PDF library/worker versions agree, adapting the patched PDF.js API, preserving real upload evidence, rejecting empty extraction, correcting image function imports, deferring transcription-client initialization, preserving prior state on persistence failure, removing fabricated mastery/citation scores, handling empty quiz results, and making chat failures retryable.

| Priority | Remaining issue | Why it remains / next validation |
|---|---|---|
| P1 before shared deployment | No authenticated ownership of sessions, learner IDs, uploaded content or mutations; alternate ingestion API remains local-only | Requires a product identity/tenant model and deployment boundary. CORS and an optional admin token are not substitutes. Do not expose publicly as-is. |
| P1 before durable multiworker deployment | In-memory coordination, learner caches per worker, JSON corpus/graph persistence lacks a cross-file crash transaction | Requires a coherent persistence/transaction design and crash/concurrency tests. Failed live ingestion now preserves the active bundle; separate corpus/graph files can still disagree after a partial disk commit or crash. |
| P1 for fully adaptive uploaded courses | Quiz bank and displayed assessment graph remain curated examples; source references may be absent | A measured ingestion→concept→verified-question pipeline needs real representative course fixtures and authorized provider evaluation. It was not synthesized from invented evidence. |
| P1 for untrusted large media | Byte cap does not bound decompression, media decoding, model compute, or total corpus size; parser processes are not isolated | Add process/time/memory budgets and representative adversarial local media fixtures before enabling public uploads. Failed multi-file processing is not a transactional corpus/file rollback. |
| P2 | Remaining 16 moderate npm findings in ESLint/minimatch dependency chains | Audit proposes incompatible major downgrades for some chains. No forced major transitive overrides were applied. Track compatible upstream updates and rerun lint/audit. |
| P2 | Python dependency reproducibility and vulnerability coverage | Root requirements use broad minimums; backend freeze differs and includes platform-specific packages. No clean-environment full ML-stack resolution or Python advisory scan was completed. |
| P2 | Browser regressions, frontend lint and accessibility | Type/build/API tests pass; session-switch races, media previews, keyboard/focus management and full UI error flows still need automated browser tests. |
| P2 | Source identity and ingest lifecycle | Same-stem files can collide in parser unit IDs, and document graph IDs normalize spaces/hyphens to underscores (for example `lecture-1.txt` and `lecture_1.txt` share a node); startup may reprocess files and call providers; failed replacements can leave file/corpus disagreement. Requires a versioned source-ID and ingestion-commit contract with migration tests. |
| P2 | Assessment semantics and replay | Exact text/numeric grading is conservative; semantic equivalents/fractions need grounded judging. Answer resubmissions can count as new observations; attempt IDs/idempotency require an explicit assessment-attempt contract. |
| P2 | Grounding security/quality | Lexical claim overlap is not semantic entailment and does not prove prompt-injection resistance. Evaluate adversarial documents and real courses; no quality gains claimed. |

Advisory evidence: [Next.js advisory](https://github.com/advisories/GHSA-2464-fhr4-w9xw), [Next.js 16.4.4 release](https://github.com/vercel/next.js/releases/tag/v16.4.4), [PDF.js advisory](https://github.com/advisories/GHSA-wgrm-67xf-hhpq). Local audit summaries and verification results are recorded in `audit_evidence.json` beside this report.
