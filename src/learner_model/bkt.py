"""
bkt.py  --  Bayesian Knowledge Tracing: the learner model.

Decision 4 (BKT parameters): prior 0.30, guess 0.20, slip 0.10, learn 0.15.
These are standard starting values; they can be tuned later with real data.

The idea in plain words:
  - Each concept has a running mastery estimate P(L) in [0, 1].
  - After every answer we (1) update P(L) with Bayes' rule, then (2) add the
    chance the student learned something on this step.
  - A correct answer raises confidence but never proves mastery, because the
    student may have guessed.
"""

from dataclasses import dataclass
import math


def _probability(value, name):
    """Reject corrupted state rather than silently persisting NaN or a bad bound."""
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite probability in [0, 1].")
    return float(value)


@dataclass
class BKTParams:
    prior: float = 0.30   # P(L0): chance the student already knows it
    guess: float = 0.20   # P(correct | not learned): correct by luck
    slip: float = 0.10    # P(wrong | learned): careless mistake
    learn: float = 0.15   # P(learn on this opportunity)

    def __post_init__(self):
        self.validate()

    def validate(self):
        for name in ("prior", "guess", "slip", "learn"):
            _probability(getattr(self, name), name)


class BKTConcept:
    """Tracks mastery for a single concept."""

    def __init__(self, concept_id, params=None, mastery=None):
        self.concept_id = concept_id
        self.params = params or BKTParams()
        self.mastery = _probability(self.params.prior if mastery is None else mastery, "mastery")

    def update(self, correct: bool, learning_opportunity: bool = True) -> float:
        """Update mastery after one observation and return the new value."""
        p = self.params
        p.validate()
        _probability(self.mastery, "mastery")
        if not isinstance(correct, bool) or not isinstance(learning_opportunity, bool):
            raise ValueError("Observation and learning_opportunity must be booleans.")
        if correct:
            # Bayes: P(L | correct)
            num = self.mastery * (1 - p.slip)
            den = self.mastery * (1 - p.slip) + (1 - self.mastery) * p.guess
        else:
            # Bayes: P(L | wrong)
            num = self.mastery * p.slip
            den = self.mastery * p.slip + (1 - self.mastery) * (1 - p.guess)

        posterior = num / den if den > 0 else self.mastery

        # Learning transition: chance of learning on this opportunity.
        if learning_opportunity:
            self.mastery = posterior + (1 - posterior) * p.learn
        else:
            self.mastery = posterior
        return self.mastery

    def decay(self, days: float, half_life_days: float = 30.0) -> float:
        """Forgetting curve: mastery fades if not reviewed (Decision: half-life 30 days)."""
        _probability(self.mastery, "mastery")
        if not math.isfinite(days) or days < 0:
            raise ValueError("days must be finite and nonnegative.")
        if not math.isfinite(half_life_days) or half_life_days <= 0:
            raise ValueError("half_life_days must be finite and positive.")
        factor = 0.5 ** (days / half_life_days)
        self.mastery *= factor
        return self.mastery


class LearnerModel:
    """Holds one BKTConcept per concept for a single student."""

    def __init__(self, concept_ids, params=None, default_mastery=None):
        self.concepts = {
            cid: BKTConcept(cid, params, default_mastery) for cid in concept_ids
        }

    def mastery(self, concept_id) -> float:
        return self.concepts[concept_id].mastery

    def all_masteries(self) -> dict:
        return {cid: c.mastery for cid, c in self.concepts.items()}

    def observe(self, concept_id, correct: bool, learning_opportunity: bool = True) -> float:
        """Fold in an answer; diagnostics measure knowledge without a learning step."""
        return self.concepts[concept_id].update(correct, learning_opportunity=learning_opportunity)

    def apply_diagnostic(self, results: dict):
        """results: {concept_id: bool}. Set starting mastery from a short diagnostic."""
        for cid, correct in results.items():
            if cid in self.concepts:
                self.concepts[cid].update(correct, learning_opportunity=False)
