import pytest
from scripts.benchmark_grounding_contract import CASES, SOURCE, make_tutor
from src.retrieval.llm import LLMError


@pytest.mark.parametrize("name,source,text,quote,expected", CASES)
def test_grounding_contract(name, source, text, quote, expected):
    claim = {"text": text, "unit_ids": ["physics-1"]}
    if quote is not None:
        claim["evidence"] = [{"unit_id": "physics-1", "quote": quote}]
    result = make_tutor(source, claim).answer("Explain acceleration and force.")
    assert any(c.text == text for c in result.claims) == expected
    if expected:
        assert result.verification == "lexical"
        assert result.confidence_kind == "accepted_claim_fraction"


class Verifier:
    name = "scripted-verifier"
    def __init__(self, verdict):
        self.verdict = verdict
    def generate_json(self, system, prompt):
        if "fact checker" in system:
            if isinstance(self.verdict, Exception):
                raise self.verdict
            return self.verdict
        return {"answerable": True, "claims": [{"text": "Acceleration is proportional to net force at constant mass.",
                                                "unit_ids": ["physics-1"]}]}


@pytest.mark.parametrize("verdict", [None, {}, {"verdicts": "yes"},
    {"verdicts": [{"i": 0, "supported": "true"}]},
    {"verdicts": [{"i": 0, "supported": True}, {"i": 0, "supported": True}]},
    LLMError("synthetic unavailable")])
def test_requested_malformed_verifier_falls_back_to_excerpts(verdict):
    result = make_tutor(SOURCE, {}, verifier=Verifier(verdict)).answer("Explain acceleration and force.")
    assert result.mode == "extractive"
    assert result.verification == "extractive"


def test_absent_verdict_cannot_approve_claim():
    result = make_tutor(SOURCE, {}, verifier=Verifier({"verdicts": []})).answer("Explain acceleration and force.")
    assert not result.claims and result.status == "refused"


def test_quote_locates_late_evidence_without_implying_semantic_proof():
    quote = "At constant mass, acceleration is proportional to net force."
    source = "Preamble. " * 80 + quote
    result = make_tutor(source, {"text": quote, "unit_ids": ["physics-1"],
                        "evidence": [{"unit_id": "physics-1", "quote": quote}]}).answer("Explain acceleration and force.")
    citation = result.sources[0]
    assert citation.excerpt_start > 300
    assert source[citation.excerpt_start:citation.excerpt_end] == citation.excerpt == quote
    assert result.claims[0].quote_validated and result.claims[0].verification == "lexical"


def test_model_approval_is_labelled_as_model_checked():
    result = make_tutor(SOURCE, {}, verifier=Verifier({"verdicts": [{"i": 0, "supported": True}]})).answer("Explain acceleration and force.")
    assert result.verification == "model_checked"


def test_two_quotes_in_one_unit_keep_distinct_inspectable_citations():
    from src.retrieval.answer import GroundedAnswerer
    from src.retrieval.schemas import Claim, ContentUnit, Location, AnswerStatus, make_citation
    unit = ContentUnit(unit_id="u", source_id="source.txt", source_type="pdf", location=Location(page=1),
                       text="Mass is measured in kilograms. Force is measured in newtons.")
    claims = [Claim(text=quote, citations=[make_citation(unit, quote)]) for quote in unit.text.split(". ")]
    result = GroundedAnswerer._compose({"question": "Units?"}, claims, [], AnswerStatus.GROUNDED,
                                       mode="generative", confidence=1, message=None)
    assert len(result.sources) == 2 and "[1]" in result.answer and "[2]" in result.answer
