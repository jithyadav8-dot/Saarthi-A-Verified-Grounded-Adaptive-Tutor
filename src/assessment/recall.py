"""Low-stakes exact-term recall derived from complete sentences in the live corpus."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import unicodedata

from src.retrieval.schemas import ContentUnit

# Only use short noun phrases followed by an explicit definition or relationship.
# Examples: "A derivative measures ...", "Momentum is defined as ...".
DEFINITION = re.compile(
    r"^(?P<term>[A-Za-z][\w-]*(?: [A-Za-z][\w-]*){0,4}?) "
    r"(?P<clue>(?:is defined as|refers to|measures|describes|represents|equals|is|are) .{12,220})[.!?]$",
    re.IGNORECASE,
)


def normalize_term(text):
    words = unicodedata.normalize("NFKC", text).casefold().strip().strip(".").split()
    if words and words[0] in {"the", "a", "an"}:
        words = words[1:]
    return " ".join(words)


@dataclass(frozen=True)
class RecallItem:
    key: str
    answer: str
    prompt: str
    quote: str
    unit: ContentUnit


def recall_items(units, limit=5):
    items, seen = [], set()
    for unit in units:
        # Unified ingestion prepends a source locator to the first sentence.
        body = re.sub(r"^(?:Slide \d+|Page \d+|Video @[\d:]+) \(" +
                      re.escape(Path(unit.source_id).stem) + r"\): ", "", unit.text, count=1)
        for line in re.split(r"(?<=[.!?])\s+|\n+", body):
            quote = line.strip()
            match = DEFINITION.fullmatch(quote)
            if not match:
                continue
            term, clue = match.group("term", "clue")
            normal = normalize_term(term)
            if (len(normal) < 3 or normal in seen or normal.split()[0] in
                    {"it", "this", "that", "they", "there", "these", "those", "we", "you"} or
                    re.search(r"\b" + re.escape(normal) + r"\b", clue.casefold())):
                continue
            digest = sha256("\0".join((unit.source_id, unit.unit_id, quote)).encode()).hexdigest()
            items.append(RecallItem(digest, term, "_____ " + clue + quote[-1], quote, unit))
            seen.add(normal)
            if len(items) >= limit:
                return items
    return items
