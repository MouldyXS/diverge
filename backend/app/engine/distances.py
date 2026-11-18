"""Cosine similarity and cosine distance. Pure NumPy, no model and no FastAPI.

    similarity(a, b) = a . b / (|a| |b|)        in [-1, 1]
    distance(a, b)   = 1 - similarity(a, b)     in [0, 2]

Computed in float64 from the given vectors, with no clipping, exactly as `row_cosine` in
`experiments/embedding_poc/embedding.py`, which produced the DAT7 baseline. Pairs of a set are enumerated in the
order of `itertools.combinations` (i < j).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from .errors import EngineInputError


def _as_matrix(vectors: object, name: str) -> np.ndarray:
    try:
        array = np.asarray(vectors)
    except Exception as exc:  # noqa: BLE001 - reported as an input error
        raise EngineInputError(f"{name}: cannot be read as an array") from exc
    if array.dtype.kind not in "fiu":
        raise EngineInputError(f"{name}: numeric values expected, got dtype {array.dtype}")
    if array.ndim != 2:
        raise EngineInputError(f"{name}: a 2-D array of shape (n, dimension) is expected, got {array.ndim}-D")
    if array.shape[1] < 1:
        raise EngineInputError(f"{name}: vectors must have at least one dimension")
    array = array.astype(np.float64)
    if not np.isfinite(array).all():
        raise EngineInputError(f"{name}: non-finite values (NaN or infinity)")
    if (np.linalg.norm(array, axis=1) == 0).any():
        raise EngineInputError(f"{name}: a zero vector has no cosine similarity")
    return array


def _row_cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cosine of two float64 matrices of the same shape (same formula as embedding.row_cosine)."""
    return np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def cosine_similarity(a: object, b: object) -> float:
    """Cosine similarity of two 1-D vectors of the same dimension."""
    va = np.asarray(a)
    vb = np.asarray(b)
    if va.ndim != 1 or vb.ndim != 1:
        raise EngineInputError("two 1-D vectors are expected")
    if va.shape != vb.shape:
        raise EngineInputError(f"incompatible dimensions: {va.shape[0]} and {vb.shape[0]}")
    ma = _as_matrix(va[None, :], "vector a")
    mb = _as_matrix(vb[None, :], "vector b")
    return float(_row_cosine(ma, mb)[0])


def cosine_distance(a: object, b: object) -> float:
    """Cosine distance 1 - cosine similarity of two 1-D vectors of the same dimension."""
    return 1.0 - cosine_similarity(a, b)


@dataclass(frozen=True)
class Pairwise:
    """All pairs (i < j) of a set of vectors, in `itertools.combinations` order."""

    pairs: tuple[tuple[int, int], ...]
    similarities: np.ndarray  # float64, shape (n_pairs,)
    distances: np.ndarray  # float64, shape (n_pairs,)


def pairwise(vectors: object) -> Pairwise:
    """Cosine similarity and distance for every pair of rows of `vectors`, shape (n, dimension) with n >= 2."""
    matrix = _as_matrix(vectors, "vectors")
    if matrix.shape[0] < 2:
        raise EngineInputError("at least two vectors are needed")
    pairs = tuple(itertools.combinations(range(matrix.shape[0]), 2))
    left, right = zip(*pairs)
    similarities = _row_cosine(matrix[list(left)], matrix[list(right)])
    return Pairwise(pairs=pairs, similarities=similarities, distances=1.0 - similarities)
