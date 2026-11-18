"""DAT7, historical and optional under D21 (docs/scoring.md section 1).

The first seven eligible, unique entries in entry order; their 21 pairs; index = mean distance x 100, in [0, 200],
with no clipping. With fewer than seven eligible entries no index is produced. This is the DAT-line protocol kept for
reference; it is not the center of the product, and the index is not a measure of creativity.

Selection, in entry order (`select_dat7`):

1. The P0 rules are applied to every entry, exactly as before. P0-invalid entries are skipped, as historically.
2. The selection is the first seven P0-eligible entries (fewer if there are not enough).
3. With an embedder, the tokens of those selected entries only are counted, once, before anything is encoded. If any
   of them is above the model context (the limit is inclusive), the whole request is rejected with
   `EngineValidationError`: the long entry is neither truncated nor skipped, no later entry replaces it, nothing is
   encoded and no index is produced. Entries after the selection play no part and are not counted.

`select_dat7` without an embedder applies the P0 rules only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .analysis import SetAnalysis, analyze_vectors
from .embedder import Embedder
from .errors import EngineValidationError
from .validation import EntryReport, check_entries, check_lengths

DAT7_WORDS = 7


@dataclass(frozen=True)
class Dat7Selection:
    checks: tuple[EntryReport, ...]  # one report per entry, in entry order
    words: tuple[str, ...]  # the first seven eligible words, or fewer if not enough

    @property
    def complete(self) -> bool:
        return len(self.words) == DAT7_WORDS


@dataclass(frozen=True)
class Dat7Result:
    selection: Dat7Selection
    analysis: SetAnalysis | None
    index: float | None  # None when fewer than seven eligible entries


def select_dat7(entries: Sequence[str], embedder: Embedder | None = None) -> Dat7Selection:
    """The first seven P0-eligible entries, in entry order.

    With an embedder, the selected entries must fit the model context; otherwise `EngineValidationError` is raised
    with one report per entry (only the selected entries carry token counts). Nothing is encoded here.
    """
    checks = check_entries(entries)
    selected = [c for c in checks if c.eligible][:DAT7_WORDS]
    lengths = {}
    if embedder is not None:
        lengths = {c.position: length for c, length in zip(selected, check_lengths(embedder, [c.normalized for c in selected]))}
    reports = tuple(
        EntryReport(c.position, c.entry, c.normalized, c.reasons + lengths[c.position].reasons,
                    lengths[c.position].tokens, lengths[c.position].max_tokens)
        if c.position in lengths else EntryReport(c.position, c.entry, c.normalized, c.reasons, None, None)
        for c in checks
    )
    too_long = [r for r in reports if r.position in lengths and not r.eligible]
    if too_long:
        detail = "; ".join(f"position {r.position} {r.entry!r}: {', '.join(r.reasons)}" for r in too_long)
        raise EngineValidationError(f"invalid entries: {detail}", entries=reports)
    return Dat7Selection(checks=reports, words=tuple(c.normalized for c in selected))


def dat7_index(analysis: SetAnalysis) -> float:
    """mean(1 - cos) x 100 over the 21 pairs of seven words."""
    if len(analysis.words) != DAT7_WORDS:
        raise ValueError(f"DAT7 needs exactly {DAT7_WORDS} words, got {len(analysis.words)}")
    return analysis.mean_distance * 100.0


def analyze_dat7(embedder: Embedder, entries: Sequence[str]) -> Dat7Result:
    selection = select_dat7(entries, embedder)  # the only validation of this analysis; raises before any encoding
    if not selection.complete:
        return Dat7Result(selection=selection, analysis=None, index=None)
    analysis = analyze_vectors(selection.words, embedder.encode(list(selection.words)))
    return Dat7Result(selection=selection, analysis=analysis, index=dat7_index(analysis))
