# Saarthi — A Verified-Grounded Adaptive Tutor

**Course-material retrieval, cited answers, prerequisite concepts, and adaptive practice.**

Saarthi is a local study-companion prototype built with **FastAPI, Next.js, and Python**. It combines document retrieval with source citations and a separate assessment workflow that tracks concept mastery using Bayesian Knowledge Tracing (BKT).

The current quiz bank and assessment graph are curated examples. Uploading a course adds retrieval content; it does **not** automatically generate a new verified question bank. Model agreement and citation checks are useful signals, not guarantees of correctness.

[Quick start](#quick-start-windows-powershell) · [Three-minute demo](docs/JUDGE_WALKTHROUGH.md) · [Implementation report](docs/improvement-audit/IMPLEMENTATION_REPORT.md) · [Controlled benchmarks](docs/improvement-audit/BENCHMARK_RESULTS.md) · [Pramana comparison](docs/improvement-audit/COMPARISON.md)

## What you can do

- **Practice directly from your notes.** The homepage builds up to five fill-in-the-blank recall cards from definition sentences in a selected source. Each answer reveals the exact passage and its location. Practice missed terms in a second round. This local word-recall exercise is separate from the curated BKT quiz.

- **Ask questions about course material.** Hybrid BM25 and embedding retrieval supplies source excerpts, page/slide references, and available timestamps. The answerer can refuse unsupported questions or fall back to cited excerpts when a provider fails.
- **Upload material.** The unified API accepts PDF, PPTX, TXT, Markdown, and supported image/audio/video formats. Text and basic document parsing work locally; enriched image and media processing can require providers.
- **Inspect concepts and evidence.** The graph view displays the bundled curriculum, actual learner mastery when available, and source evidence when present. Missing evidence and unmeasured values are labelled explicitly.
- **Practice with adaptive quizzes.** Select difficulty, concept, and question count. Answer feedback updates local BKT mastery. Quizzes stop at the eligible unique-question pool instead of repeating questions to fill a request.
- **Resume local progress.** Chat history, evidence metadata, learner progress and issued quiz attempts persist in SQLite. An identical answer retry returns the original feedback and records one observation.
- **Search inside slides.** PPTX uploads preserve native tables, grouped text, speaker notes and common Office Math forms. Citations retain the slide location.
- **Compare simulated selection policies.** The benchmark uses the same simulated learning rule for adaptive and random selection. RAGAS scores and statistical significance remain **Not measured**.

## Quick start (Windows PowerShell)

Use **Python 3.12** and **Node.js 22.13 or newer** with npm. Verification used Python 3.12.10 and Node 25.8.0. Dependency installation requires internet access; the configuration below runs retrieval and assessment without hosted models after installation.

```powershell
git clone https://github.com/jithyadav8-dot/Saarthi-A-Verified-Grounded-Adaptive-Tutor.git
cd Saarthi-A-Verified-Grounded-Adaptive-Tutor
```

### 1. Install the backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Using the virtual environment's Python directly avoids changing PowerShell's script execution policy. The Python manifest includes optional ML and media dependencies, so the first installation can be substantial.

### 2. Start the offline backend

Run these commands in the same terminal, from the repository root:

```powershell
$env:PYTHON_DOTENV_DISABLED = "1"
$env:POD_B_ENV_FILE = "nonexistent.env"
$env:EMBEDDING_PROVIDER = "hash"
$env:RERANK_PROVIDER = "lexical"
$env:LLM_PROVIDER = "none"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
.\.venv\Scripts\python.exe -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000
```

Open [API documentation](http://127.0.0.1:8000/docs) or [health status](http://127.0.0.1:8000/health). Start with the bundled material or upload a TXT/Markdown file. Existing files in `uploads/` can be reprocessed on startup; keep provider-dependent media out of that folder when using offline mode.

### 3. Start the frontend

In a second terminal, from the repository root:

```powershell
cd src/ui
npm ci
npm run dev
```

Open [Saarthi at localhost:3000](http://localhost:3000). Pages include chat, the concept graph, quizzes, and the simulation benchmark.

The frontend defaults to `http://localhost:8000`. To change it, set `NEXT_PUBLIC_API_BASE_URL` in `src/ui/.env.local`. Development and production builds copy the installed PDF.js worker locally and use system fonts.

### Optional model providers

Use a fresh terminal without the offline environment overrides. Create a local `.env` from [`.env.example`](.env.example), then configure only the providers you intend to use. Never commit real keys.

- Gemini, Groq, and Replicate adapters are available; select the provider explicitly when enabling model-backed answers.
- `EMBEDDING_PROVIDER=hash` and `RERANK_PROVIDER=lexical` keep retrieval local even when an answer model is enabled.
- Image captioning, transcription, graph building, and assessment-generation modules have their own provider requirements. Their presence does not establish end-to-end quality or connect generated questions automatically to the default quiz bank.

See [retrieval and graph architecture](docs/POD_B_ARCHITECTURE.md), [assessment handoff](docs/POD_C_HANDOFF.md), and the [current audit](docs/ENGINEERING_AUDIT.md) for implementation details and verified limits.

## Architecture

```text
Course files → parsers → ContentUnits → hybrid retrieval → cited tutor answers
                              └──────→ concept graph and source evidence

Bundled assessment bank → quiz selection → issued attempt → grade once → BKT mastery
                               ↑                              │
                               └──────────────────────────────┘

Next.js interface ↔ unified FastAPI service ↔ local files / SQLite
```

| Directory | Responsibility |
|---|---|
| [`src/api`](src/api) | Unified API, sessions, uploads, assessment and evaluation routes |
| [`src/ingestion`](src/ingestion) | Document/media parsing, chunking, checkpoints and upload validation |
| [`src/retrieval`](src/retrieval) | Hybrid search, provider adapters, cited answers and live corpus state |
| [`src/graph`](src/graph) | Concept graph, prerequisite validation and graph building |
| [`src/assessment`](src/assessment) | Question-generation modules, answer comparison and restricted SymPy checks |
| [`src/learner_model`](src/learner_model) | BKT, adaptive selection, curated bank and simulation |
| [`src/ui`](src/ui) | Next.js application and frontend checks |
| [`tests`](tests), [`scripts`](scripts) | Offline regressions, startup smoke test and evaluation utilities |
| [`backend/app`](backend/app) | Alternate ingestion service; mirrored safety changes are retained |

The unified entry point is `src.api.service:app`. Retrieval uploads publish a newly built state only after persistence succeeds. Individual graph-file writes are atomic; corpus and graph files do not yet form a crash-safe transaction.

## Verification

From the repository root, in a terminal with the offline variables shown above:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m scripts.smoke_offline
.\.venv\Scripts\python.exe -m scripts.benchmark_chunking
.\.venv\Scripts\python.exe scripts/eval_grounding.py

cd src/ui
npm test
npm run typecheck
npm run build
npm run lint
```

The Pramana comparison uses the audited baseline at `42b0b63`. The controlled workloads ran on November 5, 2026, with final regression verification on November 16.

| Check | Observed result |
|---|---|
| Python regressions | **295 passed**, including upload-to-recall grading, source replacement, repeated practice cycles and concurrent answer retries |
| Frontend API/render/callback checks | **22 passed**, including the missed-term practice round |
| TypeScript, production build, real offline server smoke | **Passed** |
| npm critical/high package findings | **2/3 → 0/0**; 16 moderate findings remain in development dependencies |
| Frontend lint | **18 errors, 27 warnings remain** |
| Simulation (seed 42) | **38.1% adaptive vs. 39.5% random** final simulated proficiency, with **517 vs. 600** questions answered |

The production browser check covered quiz submission, mastery feedback and cited offline chat. The real-server smoke also covers upload/source access, reporting and chat reload. Hosted-model accuracy, RAGAS and real learner outcomes remain unmeasured. The package findings above are from the earlier audit. See [benchmark methods and raw results](docs/improvement-audit/BENCHMARK_RESULTS.md), [next improvements](docs/improvement-audit/REMAINING_IMPROVEMENTS.md) and the [earlier engineering audit](docs/ENGINEERING_AUDIT.md).

API clients should keep the `attempt_id` returned by `/quiz` or `/diagnostic` and send it with `student_id`, `q_id` and `answer` to `/answer`. The same attempt and answer can be retried safely. Request a fresh attempt to practice again. An unissued question, a changed retry or an ambiguous ID-less submission returns HTTP 409. Diagnostics update the knowledge estimate without adding a practice learning transition.

## Operating limits

This is a **single-process local demonstration**. Student/session IDs are caller-supplied; authentication, tenant isolation and ownership checks are not implemented. Uploaded retrieval content is shared. Keep the API on loopback until those boundaries and media resource isolation are designed and tested.

- Uploads have a default **100 MiB per-file limit**, configurable with `SAARTHI_MAX_UPLOAD_BYTES`. Oversize files return `413`; empty extraction returns `422`. A byte cap does not bound decompression or model compute.
- Set `POD_B_ADMIN_TOKEN` to protect indexing and upload routes with `X-Admin-Token`. The browser deliberately contains no admin secret; protected browser uploads need a trusted proxy. Configure allowed origins with `POD_B_CORS_ORIGINS`.
- Multi-file ingestion and separate corpus/graph files lack a complete rollback/crash transaction. Multiple workers do not share coherent learner caches. Some normalized document/source IDs can collide.
- Text grading compares normalized complete answers. Numeric grading accepts finite decimal/scientific notation; semantic equivalence and fractions are not handled by that comparison.
- Dependency manifests are not a fully locked, clean-room Python environment. Remaining lint, browser coverage, and dependency findings are tracked in the audit.

## Attribution and license

The supplied project's README referenced the [original Saarthi repository](https://github.com/NansKong/Saarthi-A-Verified-Grounded-Adaptive-Tutor) and described it as developed for the Multimodal AI Hackathon 2026 under the MIT License. A standalone license text was not included in this checkout; this README does not add or replace a license grant.
