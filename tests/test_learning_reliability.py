"""Offline regression checks for assessment selection and benchmark validity."""
import pytest

from src.learner_model.adaptive import build_quiz
from src.learner_model.live_course_data import (
    AblationSimulator,
    LIVE_COURSE_CONCEPTS,
    LIVE_QUESTION_BANK,
)
from src.mock_data import get_question_concept_id


def test_quiz_never_repeats_a_question_when_requested_size_exceeds_pool():
    quiz = build_quiz(LIVE_COURSE_CONCEPTS, {}, LIVE_QUESTION_BANK[:2], size=5)
    assert len(quiz) == len({q.q_id for q in quiz}) == 2


def test_requested_concept_does_not_fall_back_to_unrelated_questions():
    assert build_quiz(LIVE_COURSE_CONCEPTS, {}, LIVE_QUESTION_BANK,
                      target_concept="unknown", size=5) == []


def test_used_questions_remain_excluded():
    pool = LIVE_QUESTION_BANK[:2]
    assert build_quiz(LIVE_COURSE_CONCEPTS, {}, pool,
                      used_ids={q.q_id for q in pool}, size=5) == []


def test_benchmark_reports_unmeasured_statistics_honestly():
    result = AblationSimulator(LIVE_COURSE_CONCEPTS, LIVE_QUESTION_BANK).run_benchmark(2, 2)
    assert result["p_value"] is None
    assert result["ragas_metrics"] is None
    assert result["evaluation_kind"] == "simulation"


def test_same_single_question_policy_has_identical_learning_curves():
    # With one question and one concept, the two selectors cannot differ.
    # Any difference would come from the experiment, not adaptive selection.
    question = LIVE_QUESTION_BANK[0]
    cid = get_question_concept_id(question)
    concepts = [c for c in LIVE_COURSE_CONCEPTS if c.concept_id == cid]
    result = AblationSimulator(concepts, [question]).run_benchmark(30, 3, 1)
    assert result["adaptive_tutor"] == result["random_baseline"]
    assert result["question_counts"]["adaptive"] == result["question_counts"]["random"]


@pytest.mark.parametrize("students,sessions,size", [(0, 5, 4), (2, 0, 4), (2, 2, 0)])
def test_benchmark_rejects_invalid_workload(students, sessions, size):
    with pytest.raises(ValueError):
        AblationSimulator(LIVE_COURSE_CONCEPTS, LIVE_QUESTION_BANK).run_benchmark(students, sessions, size)
