"""Controlled offline audit. Run the same harness against baseline and current source.

python scripts/benchmark_improvements.py --source-root . --output results.json
No hosted providers, downloaded models, user uploads or learner records are used.
Fixtures are development cases, not independent educational-effectiveness evidence.
"""
from __future__ import annotations

import argparse
from contextlib import chdir
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
import tracemalloc
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_root, output = args.source_root.resolve(), args.output.resolve()
    sys.path.insert(0, str(source_root))
    os.environ.update(PYTHON_DOTENV_DISABLED="1", POD_B_ENV_FILE="nonexistent.env",
                      EMBEDDING_PROVIDER="hash", RERANK_PROVIDER="lexical", LLM_PROVIDER="none",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    for key in ("POD_B_CORPUS", "POD_B_GRAPH", "POD_B_CACHE_DIR", "POD_B_SOURCES_DIR", "POD_B_ADMIN_TOKEN",
                "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "REPLICATE_API_KEY", "REPLICATE_API_TOKEN"):
        os.environ.pop(key, None)
    sys.modules["env_loader"] = types.ModuleType("env_loader")
    from src.retrieval.store import CorpusStore
    from src.retrieval.embeddings import HashingEmbedder
    from src.retrieval.rerank import LexicalReranker
    from src.retrieval.bm25 import BM25
    from src.retrieval.retriever import HybridRetriever
    from src.graph.graph import KnowledgeGraph
    from src.retrieval.store import DEFAULT_GRAPH
    from src.retrieval.golden import LEXICAL, SEMANTIC, OFF_MATERIAL, NEAR_MISS
    from src.retrieval.answer import GroundedAnswerer
    from src.learner_model.live_course_data import LIVE_COURSE_CONCEPTS, LIVE_QUESTION_BANK, AblationSimulator
    from src.learner_model.adaptive import build_quiz
    from src.mock_data import get_question_concept_id
    from src.ingestion.ingestion.ppt_parser import extract_ppt_content

    tracemalloc.start()
    started = time.perf_counter()
    store = CorpusStore.from_json()
    graph = KnowledgeGraph.load(DEFAULT_GRAPH)
    retriever = HybridRetriever(store, HashingEmbedder(), LexicalReranker(BM25([u.searchable_text() for u in store.all()])._idf), graph=graph)
    index_ms = (time.perf_counter() - started) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    queries = LEXICAL + SEMANTIC
    def metrics(rankings):
        return {
            "hit_at_1": statistics.mean(bool(ids) and ids[0] in gold for ids, gold in rankings),
            "hit_at_3": statistics.mean(any(uid in gold for uid in ids[:3]) for ids, gold in rankings),
            "mrr_at_3": statistics.mean(next((1 / (i + 1) for i, uid in enumerate(ids[:3]) if uid in gold), 0) for ids, gold in rankings),
            "precision_at_3": statistics.mean(sum(uid in gold for uid in ids[:3]) / 3 for ids, gold in rankings),
            "recall_at_3": statistics.mean(len(set(ids[:3]) & set(gold)) / len(gold) for ids, gold in rankings),
        }
    rankings, times = [], []
    for query, gold in queries:
        for _ in range(5):
            start = time.perf_counter()
            hits = retriever.search(query, 3)
            times.append((time.perf_counter() - start) * 1000)
        rankings.append(([h.unit.unit_id for h in hits], gold))
    ablations = {}
    for mode in ("bm25", "hash_dense"):
        ranked = []
        for query, gold in queries:
            scores = retriever._bm25.scores(query) if mode == "bm25" else retriever._emb @ retriever.embedder.embed_query(query)
            ids = [retriever.units[i].unit_id for i in sorted(range(len(scores)), key=lambda i: -scores[i])]
            ranked.append((ids, gold))
        ablations[mode] = metrics(ranked)
    answerer = GroundedAnswerer(retriever, graph, threshold_strict=.42, threshold_permissive=.21)
    grounding = {
        "in_scope_answered": sum(answerer.answer(q).status != "refused" for q, _ in queries),
        "off_topic_refused": sum(answerer.answer(q).status == "refused" for q in OFF_MATERIAL),
        "near_miss_not_grounded": sum(answerer.answer(q).status != "grounded" for q in NEAR_MISS),
        "faithfulness": "Not measured", "semantic_citation_support": "Not measured",
    }
    masteries = {c.concept_id: .3 for c in LIVE_COURSE_CONCEPTS}
    quiz = build_quiz(LIVE_COURSE_CONCEPTS, masteries, LIVE_QUESTION_BANK, size=25)
    by_id = {c.concept_id: c for c in LIVE_COURSE_CONCEPTS}
    blocked = [q.q_id for q in quiz if any(masteries[p] < .6 for p in by_id[get_question_concept_id(q)].prerequisites)]
    simulation = AblationSimulator(LIVE_COURSE_CONCEPTS, LIVE_QUESTION_BANK).run_benchmark(30, 5, 4)
    # Use exactly the same authored PPTX fixture against each source checkout.
    fixture_path = Path(__file__).resolve().parents[1] / "tests/test_structured_slides.py"
    spec = importlib.util.spec_from_file_location("audit_slide_fixture", fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    temporary_root = Path(__file__).resolve().parents[1] / ".audit_tmp"
    with tempfile.TemporaryDirectory(dir=temporary_root, prefix="controlled-") as directory:
        work = Path(directory)
        fixture.write_fixture(work / "native.pptx")
        start = time.perf_counter()
        units = extract_ppt_content(str(work / "native.pptx"))
        slide_ms = (time.perf_counter() - start) * 1000
        text = "\n".join(u.text for u in units)
        probes = ["Newton's second law", "Mass", "2 kg", "3 m/s^2", "Grouped force diagram label", "Speaker reminder", "a = (F)/(m)"]
        with chdir(work):
            from fastapi.testclient import TestClient
            from src.api import service
            client = TestClient(service.app)
            issued = client.post("/quiz", json={"student_id": "audit", "size": 1}).json()["questions"][0]
            q = service.QUESTION_BANK[issued["q_id"]]
            body = {"student_id": "audit", "q_id": q.q_id, "answer": q.answer, "attempt_id": issued.get("attempt_id")}
            first = client.post("/answer", json=body).json()
            retry = client.post("/answer", json=body).json()
            replay = {"mastery_after_first": first["new_mastery"], "mastery_after_retry": retry["new_mastery"],
                      "history_entries": len(service.SESSIONS["audit"])}
    result = {
        "protocol": "saarthi-improvement-audit-v1", "source_root": source_root.name, "seed": 42,
        "dataset": {"corpus_units": len(store), "in_scope": len(queries), "off_topic": len(OFF_MATERIAL), "near_miss": len(NEAR_MISS),
                    "sampling": "all bundled development queries; one authored slide; one issued-answer replay"},
        "backend": "hash:512|lexical; no model downloads or hosted calls", "api_calls": 0, "api_cost": 0,
        "retrieval": metrics(rankings), "retrieval_ablations": ablations,
        "engineering": {"index_ms": index_ms, "peak_python_traced_bytes": peak,
                        "retrieval_median_ms": statistics.median(times), "retrieval_p95_ms": sorted(times)[94]},
        "grounding": grounding, "pptx": {"probes": len(probes), "recovered": sum(p in text for p in probes), "extraction_ms": slide_ms},
        "quiz": {"requested": 25, "returned": len(quiz), "prerequisite_violations": len(blocked)},
        "answer_retry": replay, "simulation": simulation,
        "limits": "Development fixtures, same author/corpus; timings are local observations, no speedup significance or real learner claim.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "retrieval": result["retrieval"], "pptx": result["pptx"],
                      "quiz": result["quiz"], "answer_retry": replay, "adaptive": simulation["final_adaptive"],
                      "random": simulation["final_random"], "question_counts": simulation["question_counts"]}, indent=2))


if __name__ == "__main__":
    main()
