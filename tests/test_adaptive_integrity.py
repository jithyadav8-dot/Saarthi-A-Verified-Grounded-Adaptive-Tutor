"""Selection must use observed mastery and valid learner-state probabilities."""
import math

import pytest

from src.learner_model.adaptive import build_quiz
from src.learner_model.bkt import BKTConcept, BKTParams, LearnerModel
from src.learner_model.live_course_data import LIVE_COURSE_CONCEPTS, LIVE_QUESTION_BANK
from src.mock_data import get_question_concept_id
from src.schemas.models import ConceptNode, Question


def item(cid, index):
    return Question(q_id=f"sim_{cid}_1_{index}", topic=cid, source_location={},
                    difficulty=1, type="short", stem=f"Question {index}", answer="yes", verified=True)


def test_adaptive_quiz_never_uses_blocked_fallback():
    masteries = {c.concept_id: .3 for c in LIVE_COURSE_CONCEPTS}
    quiz = build_quiz(LIVE_COURSE_CONCEPTS, masteries, LIVE_QUESTION_BANK, size=25)
    by_id = {c.concept_id: c for c in LIVE_COURSE_CONCEPTS}
    assert quiz
    assert all(all(masteries[p] >= .6 for p in by_id[get_question_concept_id(q)].prerequisites)
               for q in quiz)
    assert len(quiz) == 11  # only the three root concepts have available items


def test_planning_questions_cannot_unlock_a_prerequisite():
    concepts = [ConceptNode(concept_id="root", name="Root", topic="T"),
                ConceptNode(concept_id="child", name="Child", topic="T", prerequisites=["root"])]
    masteries = {"root": .59, "child": .1}
    quiz = build_quiz(concepts, masteries, [item("root", 0), item("root", 1), item("child", 0)], size=3)
    assert [get_question_concept_id(q) for q in quiz] == ["root", "root"]
    assert masteries == {"root": .59, "child": .1}


def test_explicit_concept_practice_remains_available():
    quiz = build_quiz(LIVE_COURSE_CONCEPTS, {}, LIVE_QUESTION_BANK,
                      target_concept="c-pca", size=4)
    assert len(quiz) == 4
    assert all(get_question_concept_id(q) == "c-pca" for q in quiz)


def test_exhausted_ready_pool_does_not_leak_unknown_or_blocked_items():
    concepts = [ConceptNode(concept_id="root", name="Root", topic="T"),
                ConceptNode(concept_id="child", name="Child", topic="T", prerequisites=["root"])]
    assert build_quiz(concepts, {"root": .2}, [item("child", 0), item("unknown", 0)]) == []


@pytest.mark.parametrize("field", ["prior", "guess", "slip", "learn"])
@pytest.mark.parametrize("invalid", [-.01, 1.01, float("nan"), float("inf")])
def test_bkt_rejects_invalid_parameters(field, invalid):
    with pytest.raises(ValueError):
        BKTParams(**{field: invalid})


@pytest.mark.parametrize("invalid", [-.01, 1.01, float("nan"), float("inf")])
def test_bkt_rejects_invalid_initial_mastery(invalid):
    with pytest.raises(ValueError):
        BKTConcept("c", mastery=invalid)


@pytest.mark.parametrize("days,half_life", [(-1, 30), (1, 0), (1, -1), (math.inf, 30), (1, math.nan)])
def test_decay_rejects_invalid_times_without_mutation(days, half_life):
    concept = BKTConcept("c")
    with pytest.raises(ValueError):
        concept.decay(days, half_life)
    assert concept.mastery == .3


def test_default_bkt_equations_are_preserved_and_diagnostic_does_not_teach():
    practice, diagnostic = LearnerModel(["c"]), LearnerModel(["c"])
    posterior = (.3 * .9) / (.3 * .9 + .7 * .2)
    assert practice.observe("c", True) == pytest.approx(posterior + (1 - posterior) * .15)
    assert diagnostic.observe("c", True, learning_opportunity=False) == pytest.approx(posterior)


def test_bkt_zero_likelihood_is_finite_and_decay_halves_mastery():
    concept = BKTConcept("c", BKTParams(prior=0, guess=0, slip=0, learn=0))
    assert concept.update(True) == 0
    concept = BKTConcept("c", mastery=.8)
    assert concept.decay(30) == pytest.approx(.4)
