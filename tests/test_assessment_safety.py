"""Regression tests for grading and the untrusted numeric-expression boundary."""
import pytest

from src.assessment.sympy_check import evaluate
from src.assessment.verifier import answers_match, verify_question
from src.schemas.models import Question


@pytest.mark.parametrize("submitted,expected,kind", [
    ("", "correct answer", "short"), (" ", "answer", "mcq"),
    ("incorrect", "correct", "short"), ("not increasing", "increasing", "short"),
    ("5", "15", "mcq"), ("1e3", "3", "numeric"),
    ("calculation 7, final 3", "3", "numeric"),
    ("nan", "nan", "numeric"), ("inf", "inf", "numeric"),
])
def test_wrong_or_empty_answers_do_not_pass(submitted, expected, kind):
    assert not answers_match(submitted, expected, kind)


@pytest.mark.parametrize("submitted,expected,kind", [
    ("  Opposite   to the gradient. ", "opposite to the gradient", "mcq"),
    ("1e3", "1000", "numeric"), (".5", "0.5", "numeric"),
    ("-2.5e-2", "-0.025", "numeric"), ("3.0000001", "3", "numeric"),
])
def test_supported_answer_formats(submitted, expected, kind):
    assert answers_match(submitted, expected, kind)


def test_dry_run_is_not_independent_verification():
    question = Question(q_id="q", topic="gradient", source_location={}, difficulty=1,
                        type="short", stem="Direction?", answer="Opposite to the gradient")
    checked, _, _ = verify_question(question, "Gradient descent moves opposite to the gradient.")
    assert not checked.verified
    assert checked.verifier_agreement == 0


@pytest.mark.parametrize("expression", [
    "__import__('builtins').len([1,2,3])",
    "(1).__class__", "open('should-never-be-opened')", "[x for x in (1,2)]",
    "2**10000", "diff(x**2, x, 10000)", "(2**100)**100",
])
def test_unsafe_or_unbounded_math_is_rejected(expression):
    with pytest.raises(ValueError):
        evaluate(expression)


@pytest.mark.parametrize("expression,subs,expected", [
    ("diff(3*x**2, x)", {"x": 2}, 12),
    ("diff((2*x+1)**3, x)", {"x": 0}, 6),
    ("0.1*5", {}, 0.5), ("sqrt(9) + sin(pi/2)", {}, 4),
])
def test_documented_numeric_calculations(expression, subs, expected):
    assert evaluate(expression, subs) == pytest.approx(expected)


@pytest.mark.parametrize("subs", [{"x": "__import__('builtins').len([1])"}, {"x": float("nan")}])
def test_substitution_values_are_finite_numbers(subs):
    with pytest.raises(ValueError):
        evaluate("x + 1", subs)


@pytest.mark.parametrize("expression", ["((2/3)**100)**100", "(2**-100)**100", "(2**100)**-100"])
def test_rational_power_size_limit_covers_reciprocals(expression):
    with pytest.raises(ValueError, match="size limit"):
        evaluate(expression)


@pytest.mark.parametrize("expression,expected", [("(2/3)**-2", 2.25), ("2**-3", .125)])
def test_small_rational_and_negative_powers_remain_supported(expression, expected):
    assert evaluate(expression) == pytest.approx(expected)
