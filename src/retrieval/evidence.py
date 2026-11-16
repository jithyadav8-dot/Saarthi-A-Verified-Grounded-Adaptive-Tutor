"""Cheap, conservative evidence screens. These do not establish semantic entailment."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from .text import tokenize

_NUMBER = re.compile(r"(?<![\w.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?![\w.])")
_NEGATIVE = re.compile(r"\b(?:not|no|never|without|cannot|can't|isn't|aren't|doesn't|don't|won't)\b", re.I)


def lexical_support(claim: str, passages: list[str], minimum: float) -> bool:
    """Require overlap, matching numeric literals and no obvious polarity reversal.

    Deliberately rejects unsupported numerical derivations: that needs a solver or
    qualified semantic judge. Sentence polarity is only a heuristic; comparisons,
    scope, coreference and paraphrase can still fool it or cause false rejection.
    """
    tokens = tokenize(claim)
    source = "\n".join(passages)
    source_tokens = set(tokenize(source))
    if not tokens or sum(t in source_tokens for t in tokens) / len(tokens) < minimum:
        return False
    try:
        numbers = {Decimal(x) for x in _NUMBER.findall(claim)}
        source_numbers = {Decimal(x) for x in _NUMBER.findall(source)}
    except (InvalidOperation, ValueError, OverflowError):
        return False
    if not numbers <= source_numbers:
        return False
    # Evaluate polarity against the most lexically similar sentence, so an unrelated
    # negative sentence elsewhere in a long unit cannot bless a negated claim.
    words = set(tokenize(_NEGATIVE.sub("", claim)))
    if words:
        sentences = [s for p in passages for s in re.split(r"(?<=[.!?])\s+|\n+", p) if s.strip()]
        scores = [(len(words & set(tokenize(s))) / len(words), s) for s in sentences]
        best = max((score for score, _ in scores), default=0)
        if best >= minimum:
            matches = [s for score, s in scores if score == best]
            polarity = bool(_NEGATIVE.search(claim))
            if not any(bool(_NEGATIVE.search(s)) == polarity for s in matches):
                return False
    return True


def validated_quotes(raw: object, ids: list[str], by_id: dict) -> dict[str, str] | None:
    """Return exact source quotes, or None for any invalid/partial evidence contract.

    Every cited unit must have exactly one nonempty verbatim quote. No fuzzy matching:
    offsets must identify actual characters, including math symbols and punctuation.
    """
    if not isinstance(raw, list) or not raw or not ids:
        return None
    quotes: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            return None
        uid, quote = item.get("unit_id"), item.get("quote")
        if not isinstance(uid, str) or uid not in ids or uid not in by_id or uid in quotes:
            return None
        if not isinstance(quote, str) or not quote.strip() or quote not in by_id[uid].searchable_text():
            return None
        quotes[uid] = quote
    return quotes if set(quotes) == set(ids) else None
