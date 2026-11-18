"""Descriptive interpretation of a set analysis: pure functions over numbers the engine already computed.

Nothing here computes embeddings or distances, calls a model or the network, keeps state, or writes Spanish: the output
is structured data (numbers, pair indexes and codes) from which the interface writes its own sentences. The result of
the analysis is only read, never changed.

Comparison rule. Two distances are treated as equal when they are **equal at the precision the interface shows**, four
decimals, so that a tie claimed in a sentence always matches the numbers on screen:

    q(x) = Decimal(repr(x)).quantize(Decimal("0.0001"), ROUND_HALF_UP)

This is the rule that agrees with `Intl.NumberFormat` (which rounds the shortest decimal representation, half up); Python's
`round(x, 4)` rounds the exact binary value and disagrees in rare boundary cases. Exact equality is reported separately,
so a tie at the displayed value is never presented as an exact tie.

Pairs are referenced by the indexes `i`, `j` the engine uses. For the extremes, the first listed pair is always the one
the engine reports: `closest` is the first of the exactly tied minimum pairs and `most_distant` the **last** of the
exactly tied maximum pairs (the engine takes `order[0]` and `order[-1]` of a stable ascending sort).

A failure here is an `InterpretationError`: it is raised, never turned into a partial or invented result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .analysis import SetResult

INTERPRETATION_VERSION = 1
PRECISION_DECIMALS = 4
MAX_LISTED_PAIRS = 5  # pairs listed per extreme; the total is reported apart, so the size of the output is bounded

_QUANTUM = Decimal(1).scaleb(-PRECISION_DECIMALS)

# Codes of edge cases (`flags`) and of fixed methodological warnings (`notes`).
FLAG_SINGLE_PAIR = "single_pair"  # two concepts: one pair, no internal comparison
FLAG_ALL_EQUAL_AT_PRECISION = "all_equal_at_precision"
FLAG_ALL_EXACTLY_EQUAL = "all_exactly_equal"
FLAG_TIE_AT_MIN = "tie_at_min"  # two or more pairs equal at the displayed minimum
FLAG_EXACT_TIE_AT_MIN = "exact_tie_at_min"  # ... and they are exactly equal
FLAG_TIE_AT_MAX = "tie_at_max"
FLAG_EXACT_TIE_AT_MAX = "exact_tie_at_max"
FLAGS = (FLAG_SINGLE_PAIR, FLAG_ALL_EQUAL_AT_PRECISION, FLAG_ALL_EXACTLY_EQUAL, FLAG_TIE_AT_MIN, FLAG_EXACT_TIE_AT_MIN,
         FLAG_TIE_AT_MAX, FLAG_EXACT_TIE_AT_MAX)

NOTE_RELATIVE_TO_THIS_SET = "relative_to_this_set"
NOTE_NO_REFERENCE_DISTRIBUTION = "no_reference_distribution"
NOTE_MEAN_IS_EXPERIMENTAL = "mean_is_experimental"
NOTES = (NOTE_RELATIVE_TO_THIS_SET, NOTE_NO_REFERENCE_DISTRIBUTION, NOTE_MEAN_IS_EXPERIMENTAL)


class InterpretationError(Exception):
    """The analysis result is not coherent enough to be described. The message never contains user text."""


@dataclass(frozen=True)
class PairRef:
    """A pair, by the 0-based indexes of its words in the set (i < j), as in the engine's `PairScore`."""

    i: int
    j: int


@dataclass(frozen=True)
class SetInterpretation:
    version: int
    precision_decimals: int
    n_pairs: int
    min_distance: float  # exact
    max_distance: float  # exact
    range: float  # max_distance - min_distance
    min_pairs: tuple[PairRef, ...]  # tied at the displayed minimum, at most MAX_LISTED_PAIRS; the first is `closest`
    max_pairs: tuple[PairRef, ...]  # tied at the displayed maximum; the first is `most_distant`
    n_min_pairs: int  # total tied at the displayed minimum (may exceed len(min_pairs))
    n_max_pairs: int
    n_above_mean: int  # pairs whose displayed distance is above the displayed mean
    n_below_mean: int
    n_at_mean: int  # equal to the mean at the displayed precision
    flags: tuple[str, ...]
    notes: tuple[str, ...]


def quantize(value: float) -> Decimal:
    """`value` rounded to the displayed precision (see the module docstring)."""
    return Decimal(repr(float(value))).quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validated(result: SetResult):
    """The pairs, their distances and the mean, after checking that they describe one coherent set."""
    try:
        analysis = result.analysis
        words, pairs, mean = analysis.words, tuple(analysis.pairs), analysis.mean_distance
        closest, most_distant = analysis.closest, analysis.most_distant
    except AttributeError:
        raise InterpretationError("the result is not a set analysis") from None
    n = len(words)
    if n < 2 or len(pairs) != n * (n - 1) // 2:
        raise InterpretationError("the number of pairs does not match the number of words")
    seen = set()
    for pair in pairs:
        i, j = pair.i, pair.j
        if not all(isinstance(index, int) and not isinstance(index, bool) for index in (i, j)) or not 0 <= i < j < n:
            raise InterpretationError("a pair has invalid indexes")
        if (i, j) in seen:
            raise InterpretationError("a pair appears more than once")
        seen.add((i, j))
        if not _is_finite_number(pair.distance):
            raise InterpretationError("a pair has no finite distance")
    if not _is_finite_number(mean):
        raise InterpretationError("the mean distance is not finite")
    distances = [float(pair.distance) for pair in pairs]
    if (closest.i, closest.j, closest.distance) != (pairs[distances.index(min(distances))].i,
                                                    pairs[distances.index(min(distances))].j, min(distances)):
        raise InterpretationError("the closest pair does not match the pairs")
    last_max = len(distances) - 1 - distances[::-1].index(max(distances))
    if (most_distant.i, most_distant.j, most_distant.distance) != (pairs[last_max].i, pairs[last_max].j, max(distances)):
        raise InterpretationError("the most distant pair does not match the pairs")
    return pairs, distances, float(mean)


def interpret_set(result: SetResult) -> SetInterpretation:
    """Describe the distribution of the distances of a set analysis. Pure: the result is not modified."""
    pairs, distances, mean = _validated(result)
    shown = [quantize(d) for d in distances]
    shown_min, shown_max = min(shown), max(shown)

    min_group = sorted((k for k, q in enumerate(shown) if q == shown_min), key=lambda k: (distances[k], k))
    max_group = sorted((k for k, q in enumerate(shown) if q == shown_max), key=lambda k: (-distances[k], -k))

    def refs(group: list[int]) -> tuple[PairRef, ...]:
        return tuple(PairRef(pairs[k].i, pairs[k].j) for k in group[:MAX_LISTED_PAIRS])

    def exactly_equal(group: list[int]) -> bool:
        return len(group) >= 2 and all(distances[k] == distances[group[0]] for k in group)

    shown_mean = quantize(mean)
    above = sum(1 for q in shown if q > shown_mean)
    below = sum(1 for q in shown if q < shown_mean)
    at_mean = len(shown) - above - below

    flags: list[str] = []
    if len(pairs) == 1:
        flags.append(FLAG_SINGLE_PAIR)
    else:
        if shown_min == shown_max:
            flags.append(FLAG_ALL_EQUAL_AT_PRECISION)
            if len(set(distances)) == 1:
                flags.append(FLAG_ALL_EXACTLY_EQUAL)
            # Equal values can differ from their mean in the last bit; the sentence must not contradict itself.
            above, below, at_mean = 0, 0, len(shown)
        if len(min_group) >= 2:
            flags.append(FLAG_TIE_AT_MIN)
            if exactly_equal(min_group):
                flags.append(FLAG_EXACT_TIE_AT_MIN)
        if len(max_group) >= 2:
            flags.append(FLAG_TIE_AT_MAX)
            if exactly_equal(max_group):
                flags.append(FLAG_EXACT_TIE_AT_MAX)

    minimum, maximum = min(distances), max(distances)
    return SetInterpretation(
        version=INTERPRETATION_VERSION, precision_decimals=PRECISION_DECIMALS, n_pairs=len(pairs),
        min_distance=minimum, max_distance=maximum, range=maximum - minimum,
        min_pairs=refs(min_group), max_pairs=refs(max_group), n_min_pairs=len(min_group), n_max_pairs=len(max_group),
        n_above_mean=above, n_below_mean=below, n_at_mean=at_mean, flags=tuple(flags), notes=NOTES,
    )


__all__ = [
    "FLAGS", "INTERPRETATION_VERSION", "MAX_LISTED_PAIRS", "NOTES", "PRECISION_DECIMALS", "InterpretationError", "PairRef",
    "SetInterpretation", "interpret_set", "quantize",
]
