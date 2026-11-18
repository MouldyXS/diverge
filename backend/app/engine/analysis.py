"""Pair analysis (the main unit, D21) and set analysis (all pairs of n words).

The mean distance of a set is an experimental indicator only: it is not a measure of creativity or of any cognitive
ability. Its presentation scale is pending (D21 section 10); this module returns the plain mean distance.

Every analysis validates its entries **once**, before anything is encoded (`validation.validate_entries`): the
deterministic P0 rules, then the token count of every normalized entry against the model context. If any entry is
invalid, it raises `EngineValidationError` (a subclass of `EngineInputError`) with a report for every entry, and
`encode` is never called; nothing is dropped. Otherwise the words are encoded with one `embedder.encode` call, in
entry order. Whether a pair gives exactly the same vectors alone and inside a larger request is not assumed (pending,
D21).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .distances import pairwise
from .embedder import Embedder
from .errors import EngineInputError, EngineValidationError
from .validation import EntryCheck, EntryReport, validate_entries


@dataclass(frozen=True)
class PairScore:
    """One pair of a set, i < j, positions starting at 0."""

    i: int
    j: int
    word_i: str
    word_j: str
    similarity: float
    distance: float


@dataclass(frozen=True)
class PairAnalysis:
    word_a: str
    word_b: str
    similarity: float
    distance: float


@dataclass(frozen=True)
class SetAnalysis:
    words: tuple[str, ...]
    pairs: tuple[PairScore, ...]
    distance_matrix: np.ndarray  # float64, symmetric, zero diagonal
    mean_distance: float  # experimental indicator, not a measure of creativity
    closest: PairScore
    most_distant: PairScore

    @property
    def n_pairs(self) -> int:
        return len(self.pairs)


def _validated(embedder: Embedder, entries: Sequence[str]) -> list[EntryReport]:
    """Validate every entry once (P0 and model context). Raise before any encoding if one is invalid."""
    reports = validate_entries(entries, embedder)
    invalid = [r for r in reports if not r.eligible]
    if invalid:
        detail = "; ".join(f"position {r.position} {r.entry!r}: {', '.join(r.reasons)}" for r in invalid)
        raise EngineValidationError(f"invalid entries: {detail}", entries=reports)
    return reports


def analyze_vectors(words: Sequence[str], vectors: object) -> SetAnalysis:
    """Set analysis from words and their vectors (row k belongs to words[k]). No model is used."""
    words = tuple(words)
    matrix = np.asarray(vectors)
    if matrix.ndim != 2 or matrix.shape[0] != len(words):
        raise EngineInputError(f"{len(words)} words but vectors of shape {matrix.shape}")
    result = pairwise(matrix)
    scores = tuple(PairScore(i, j, words[i], words[j], float(s), float(d))
                   for (i, j), s, d in zip(result.pairs, result.similarities, result.distances))
    distance_matrix = np.zeros((len(words), len(words)), dtype=np.float64)
    for score in scores:
        distance_matrix[score.i, score.j] = distance_matrix[score.j, score.i] = score.distance
    order = np.argsort(result.distances, kind="stable")
    return SetAnalysis(words=words, pairs=scores, distance_matrix=distance_matrix, mean_distance=float(result.distances.mean()),
                       closest=scores[int(order[0])], most_distant=scores[int(order[-1])])


def analyze_set(embedder: Embedder, entries: Sequence[str]) -> SetAnalysis:
    """All n(n - 1) / 2 pairs of n >= 2 valid, unique entries. No maximum is enforced (pending, D21)."""
    reports = _validated(embedder, entries)
    if len(reports) < 2:
        raise EngineValidationError("a set needs at least two words", entries=reports, problem=EngineValidationError.TOO_FEW_WORDS)
    words = [r.normalized for r in reports]
    return analyze_vectors(words, embedder.encode(words))


def analyze_pair(embedder: Embedder, word_a: str, word_b: str) -> PairAnalysis:
    """Similarity and distance of one pair of valid, different words, encoded together in one call."""
    a, b = (r.normalized for r in _validated(embedder, [word_a, word_b]))
    vectors = embedder.encode([a, b])
    result = pairwise(vectors)
    return PairAnalysis(word_a=a, word_b=b, similarity=float(result.similarities[0]), distance=float(result.distances[0]))


__all__ = ["EntryCheck", "EntryReport", "PairAnalysis", "PairScore", "SetAnalysis", "analyze_pair", "analyze_set", "analyze_vectors"]
