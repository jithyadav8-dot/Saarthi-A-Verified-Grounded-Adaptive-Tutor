"""Offline regressions for malformed and unavailable model responses."""
import httpx
import pytest

from src.retrieval.answer import GroundedAnswerer
from src.retrieval.bm25 import BM25
from src.retrieval.embeddings import HashingEmbedder
from src.retrieval.rerank import LexicalReranker
from src.retrieval.retriever import HybridRetriever
from src.retrieval.schemas import AnswerStatus


class FakeModel:
    name = "offline-regression"
    def __init__(self, reply):
        self.reply = reply
    def generate_json(self, system, prompt):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def answerer(store, graph, reply):
    retriever = HybridRetriever(store, HashingEmbedder(),
        LexicalReranker(BM25([u.searchable_text() for u in store.all()])._idf), graph=graph)
    return GroundedAnswerer(retriever, graph, FakeModel(reply),
                            threshold_strict=.42, threshold_permissive=.21)


@pytest.mark.parametrize("reply", [
    httpx.ReadTimeout("synthetic timeout"), httpx.ConnectError("synthetic disconnect"),
    {"claims": 7}, {"claims": "wrong shape"},
    {"claims": [{"text": "Chain rule", "unit_ids": 7}]},
    {"claims": [{"text": "Chain rule", "unit_ids": "sl-08"}]},
    {"claims": [], "outside_knowledge": 7},
])
def test_model_failures_degrade_to_cited_excerpts(store, graph, reply):
    result = answerer(store, graph, reply).answer("what is the chain rule")
    assert result.mode == "extractive"
    assert result.sources
    assert "unavailable" in result.message


@pytest.mark.parametrize("opt_in", [False, True])
def test_partial_response_respects_outside_knowledge_opt_in(store, graph, opt_in):
    reply = {"answerable": True, "claims": [
        {"text": "The chain rule differentiates a composition of functions.", "unit_ids": ["sl-08"]},
        {"text": "An unsupported statement.", "unit_ids": []}],
        "outside_knowledge": ["A general-knowledge note."]}
    result = answerer(store, graph, reply).answer("what is the chain rule", allow_outside_knowledge=opt_in)
    assert result.status == AnswerStatus.PARTIAL
    assert bool(result.outside_knowledge) == opt_in
    assert "unsupported" not in result.answer


def test_followup_rewrite_outage_degrades_without_failing(store, graph):
    result = answerer(store, graph, httpx.ReadTimeout("synthetic timeout")).answer(
        "and why?", history=[{"role": "user", "content": "what is the chain rule"}])
    assert result.mode == "extractive"
    assert result.sources


@pytest.mark.parametrize("body", [
    "upstream temporarily unavailable", "null", "[]",
    '{"candidates": [null]}', '{"candidates": 3}',
    '{"candidates": [{"content": null}]}',
    '{"candidates": [{"content": {"parts": null}}]}',
    '{"candidates": [{"content": {"parts": [null]}}]}',
    '{"candidates": [{"content": {"parts": [{"text": 3}]}}]}',
])
def test_malformed_provider_envelopes_degrade_to_cited_excerpts(store, graph, body):
    from src.retrieval.llm import GeminiLLM
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, text=body))) as client:
        tutor = answerer(store, graph, None)
        tutor.llm = GeminiLLM("offline-fake-key", client=client, sleep=lambda _: None)
        result = tutor.answer("what is the chain rule")
    assert result.mode == "extractive"
    assert result.sources
    assert "unavailable" in result.message
    assert body not in result.message
