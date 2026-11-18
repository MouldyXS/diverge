"""Synthetic mathematical tests of cosine similarity and distance. No model."""

import math

import numpy as np
import pytest

from app.engine import EngineInputError, cosine_distance, cosine_similarity, pairwise

EXACT = 1e-12  # float64 arithmetic on small exact vectors


def test_identical_vectors_have_distance_zero():
    v = np.array([0.3, -1.2, 2.5])
    assert cosine_similarity(v, v) == pytest.approx(1.0, abs=EXACT)
    assert cosine_distance(v, v) == pytest.approx(0.0, abs=EXACT)


def test_scaled_vector_has_distance_zero():
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_distance(v, 4.5 * v) == pytest.approx(0.0, abs=EXACT)


def test_opposite_vectors_have_distance_two():
    v = np.array([1.0, -2.0, 0.5])
    assert cosine_similarity(v, -v) == pytest.approx(-1.0, abs=EXACT)
    assert cosine_distance(v, -v) == pytest.approx(2.0, abs=EXACT)


def test_orthogonal_vectors_have_distance_one():
    a, b = np.array([1.0, 0.0, 0.0]), np.array([0.0, 3.0, 0.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0, abs=EXACT)
    assert cosine_distance(a, b) == pytest.approx(1.0, abs=EXACT)


def test_distance_is_symmetric():
    rng = np.random.default_rng(0)
    for _ in range(50):
        a, b = rng.normal(size=16), rng.normal(size=16)
        assert cosine_distance(a, b) == cosine_distance(b, a)


def test_distance_stays_in_theoretical_range():
    rng = np.random.default_rng(1)
    vectors = rng.normal(size=(40, 8))
    result = pairwise(vectors)
    assert result.distances.min() >= -EXACT
    assert result.distances.max() <= 2 + EXACT
    assert result.similarities.min() >= -1 - EXACT
    assert result.similarities.max() <= 1 + EXACT


def test_distance_equals_one_minus_similarity():
    rng = np.random.default_rng(2)
    a, b = rng.normal(size=5), rng.normal(size=5)
    assert cosine_distance(a, b) == 1.0 - cosine_similarity(a, b)


def test_pairwise_counts_and_order():
    vectors = np.eye(5, 6)
    result = pairwise(vectors)
    assert len(result.pairs) == 5 * 4 // 2
    assert result.pairs[:4] == ((0, 1), (0, 2), (0, 3), (0, 4))
    assert result.pairs[-1] == (3, 4)
    assert np.allclose(result.distances, 1.0, atol=EXACT)


def test_pairwise_matches_single_pair_function():
    rng = np.random.default_rng(3)
    vectors = rng.normal(size=(6, 10))
    result = pairwise(vectors)
    for (i, j), d in zip(result.pairs, result.distances):
        assert d == cosine_distance(vectors[i], vectors[j])


def test_float32_input_is_computed_in_float64():
    a = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    b = np.array([0.3, 0.1, 0.2], dtype=np.float32)
    a64, b64 = a.astype(np.float64), b.astype(np.float64)
    expected = float(a64 @ b64 / (math.sqrt(a64 @ a64) * math.sqrt(b64 @ b64)))
    assert cosine_similarity(a, b) == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_values_are_rejected(bad):
    a = np.array([1.0, bad, 0.0])
    with pytest.raises(EngineInputError, match="non-finite"):
        cosine_similarity(a, np.array([1.0, 0.0, 0.0]))
    with pytest.raises(EngineInputError, match="non-finite"):
        pairwise(np.vstack([a, [0.0, 1.0, 0.0]]))


def test_incompatible_dimensions_are_rejected():
    with pytest.raises(EngineInputError, match="incompatible dimensions"):
        cosine_similarity(np.ones(3), np.ones(4))


def test_zero_vector_is_rejected():
    with pytest.raises(EngineInputError, match="zero vector"):
        cosine_distance(np.zeros(3), np.ones(3))


def test_wrong_shapes_and_types_are_rejected():
    with pytest.raises(EngineInputError):
        cosine_similarity(np.ones((2, 3)), np.ones((2, 3)))
    with pytest.raises(EngineInputError, match="at least two"):
        pairwise(np.ones((1, 3)))
    with pytest.raises(EngineInputError, match="2-D"):
        pairwise(np.ones(3))
    with pytest.raises(EngineInputError, match="numeric"):
        pairwise(np.array([["a", "b"], ["c", "d"]]))
