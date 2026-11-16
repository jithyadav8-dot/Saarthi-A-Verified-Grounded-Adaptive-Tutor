"""Offline adversarial contract benchmark; scripted claims, NOT a model accuracy study.

Run unchanged before/after the implementation. No provider/environment configuration is read.
The hand-authored cases are development regressions, not independent held-out data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time

from src.retrieval.answer import GroundedAnswerer
from src.retrieval.bm25 import BM25
from src.retrieval.embeddings import HashingEmbedder
from src.retrieval.rerank import LexicalReranker
from src.retrieval.retriever import HybridRetriever
from src.retrieval.schemas import ContentUnit, Location
from src.retrieval.store import CorpusStore

SOURCE = "At constant mass, acceleration is proportional to net force. A 2 kg cart under a 6 N net force has acceleration 3 m/s^2."
CASES = [
    ("literal", SOURCE, "At constant mass, acceleration is proportional to net force.", None, True),
    ("paraphrase", SOURCE, "Acceleration is proportional to net force at constant mass.", None, True),
    ("numeric_valid", SOURCE, "A 2 kg cart under a 6 N net force has acceleration 3 m/s^2.", None, True),
    ("quote_valid", SOURCE, "Acceleration is proportional to net force at constant mass.", "At constant mass, acceleration is proportional to net force.", True),
    ("number_changed", SOURCE, "A 2 kg cart under a 6 N net force has acceleration 30 m/s^2.", None, False),
    ("negation_added", SOURCE, "At constant mass, acceleration is not proportional to net force.", None, False),
    ("negation_removed", "Friction does not create energy.", "Friction creates energy.", None, False),
    ("fabricated_quote", SOURCE, "Acceleration is proportional to net force at constant mass.", "This invented quote says acceleration is proportional to force.", False),
    ("irrelevant_quote", SOURCE + " The cart is blue.", "Acceleration is proportional to net force at constant mass.", "The cart is blue.", False),
]


class ScriptedModel:
    name = "offline-scripted-contract-v1"

    def __init__(self, claim: dict):
        self.claim = claim

    def generate_json(self, system, prompt):
        return {"answerable": True, "claims": [self.claim]}


def make_tutor(source: str, claim: dict, *, verifier=None):
    unit = ContentUnit(unit_id="physics-1", source_id="fixture.txt", source_type="pdf",
                       location=Location(page=1), text=source)
    store = CorpusStore([unit])
    retriever = HybridRetriever(store, HashingEmbedder(), LexicalReranker(BM25([source])._idf))
    model = verifier or ScriptedModel(claim)
    return GroundedAnswerer(retriever, None, model, threshold_strict=0, threshold_permissive=0,
                            verify_with_llm=verifier is not None)


def run() -> dict:
    rows, latencies = [], []
    for name, source, claim_text, quote, expected in CASES:
        claim = {"text": claim_text, "unit_ids": ["physics-1"]}
        if quote is not None:
            claim["evidence"] = [{"unit_id": "physics-1", "quote": quote}]
        tutor = make_tutor(source, claim)
        samples = []
        for _ in range(7):
            start = time.perf_counter()
            answer = tutor.answer("Explain acceleration and force.")
            samples.append((time.perf_counter() - start) * 1000)
        accepted = any(c.text == claim_text for c in answer.claims)
        rows.append({"case": name, "expected_accept": expected, "accepted": accepted,
                     "status": answer.status.value, "mode": answer.mode})
        latencies.extend(samples)
    valid = [r for r in rows if r["expected_accept"]]
    invalid = [r for r in rows if not r["expected_accept"]]
    return {"protocol": "grounding-contract-v1", "seed": None,
            "conditions": "hash:512|lexical; one source per case; scripted generator; zero gate thresholds; 7 repeats",
            "scope": "Development contract regression, not faithfulness, real model hallucination rate, or educational effectiveness",
            "cases": len(rows), "valid_accepted": sum(r["accepted"] for r in valid), "valid_total": len(valid),
            "invalid_rejected": sum(not r["accepted"] for r in invalid), "invalid_total": len(invalid),
            "median_answer_ms": statistics.median(latencies), "api_calls": 0, "api_cost": 0,
            "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    encoded = json.dumps(result, indent=2)
    print(encoded)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
