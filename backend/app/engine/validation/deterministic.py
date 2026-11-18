"""Deterministic format rules of P0 (docs/scoring.md sections 5 and 7): one word, no digits or symbols, no repetition.

These rules check format only. They do not check that a word exists in Spanish or that it is a noun. The behavior
matches the rule used by the DAT7 baseline (`experiments/results/semantic_baseline_dat7_v0.1/run_baseline.py`):

* an empty entry is `empty`; otherwise an entry with whitespace is `multiple_words`; otherwise an entry that is not
  made only of letters is `digit_or_symbol`;
* a non-empty entry equal, after normalization, to an earlier *eligible* entry is also `duplicate`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..normalize import normalize

EMPTY = "empty"
MULTIPLE_WORDS = "multiple_words"
DIGIT_OR_SYMBOL = "digit_or_symbol"
DUPLICATE = "duplicate"


@dataclass(frozen=True)
class EntryCheck:
    """Result of the deterministic rules for one entry, in entry order (position starts at 1)."""

    position: int
    entry: str
    normalized: str
    reasons: tuple[str, ...]

    @property
    def eligible(self) -> bool:
        return not self.reasons


def check_entries(entries: Sequence[str]) -> list[EntryCheck]:
    """Apply the deterministic rules to every entry, in order. Nothing is dropped: every entry gets a result."""
    seen: set[str] = set()
    results: list[EntryCheck] = []
    for position, entry in enumerate(entries, 1):
        word = normalize(entry)
        reasons: list[str] = []
        if not word:
            reasons.append(EMPTY)
        elif any(ch.isspace() for ch in word):
            reasons.append(MULTIPLE_WORDS)
        elif not word.isalpha():
            reasons.append(DIGIT_OR_SYMBOL)
        if word and word in seen:
            reasons.append(DUPLICATE)
        if not reasons:
            seen.add(word)
        results.append(EntryCheck(position=position, entry=entry, normalized=word, reasons=tuple(reasons)))
    return results
