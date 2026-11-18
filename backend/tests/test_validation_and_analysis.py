"""Normalization, deterministic validation, pair and set analysis and DAT7 selection, with a synthetic embedder. No model."""

import unicodedata

import numpy as np
import pytest

from app.engine import (EngineInputError, analyze_dat7, analyze_pair, analyze_set, analyze_vectors, check_entries, dat7_index,
                        normalize, select_dat7)


class FakeEmbedder:
    """Deterministic vectors per word; records every call, so the number and order of calls can be checked.

    Token counts are `len(text) + 2` (two special tokens), with a 512-token limit, so ordinary words always fit.
    """

    max_input_tokens = 512

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension
        self.calls: list[list[str]] = []

    def count_tokens(self, texts):
        return [len(text) + 2 for text in texts]

    def encode(self, texts):
        self.calls.append(list(texts))
        rows = []
        for text in texts:
            seed = sum(ord(c) * (k + 1) for k, c in enumerate(text))
            rows.append(np.random.default_rng(seed).normal(size=self.dimension))
        return np.vstack(rows).astype(np.float32)

    def describe(self):
        return {"model_id": "fake"}


def test_normalize_strip_casefold_and_nfc():
    assert normalize("  Árbol ") == "árbol"
    assert normalize(unicodedata.normalize("NFD", "AÑO")) == "año"
    assert normalize("año") != normalize("ano")


def test_normalize_rejects_non_strings():
    with pytest.raises(EngineInputError):
        normalize(3)


def test_deterministic_rules():
    checks = check_entries(["perro", "", "dos palabras", "casa1", "Perro", "!", "gato"])
    reasons = [c.reasons for c in checks]
    assert reasons == [(), ("empty",), ("multiple_words",), ("digit_or_symbol",), ("duplicate",), ("digit_or_symbol",), ()]
    assert [c.position for c in checks] == [1, 2, 3, 4, 5, 6, 7]
    assert len(checks) == 7  # nothing dropped


def test_diacritic_pairs_are_distinct_words():
    checks = check_entries(["sí", "si", "año", "ano", "papá", "papa"])
    assert all(c.eligible for c in checks)


def test_analyze_pair_encodes_once_in_order():
    embedder = FakeEmbedder()
    result = analyze_pair(embedder, " Casa", "perro")
    assert embedder.calls == [["casa", "perro"]]
    assert (result.word_a, result.word_b) == ("casa", "perro")
    assert result.distance == pytest.approx(1.0 - result.similarity, abs=0)
    assert 0.0 <= result.distance <= 2.0


@pytest.mark.parametrize("pair", [("casa", ""), ("casa", "Casa"), ("dos palabras", "casa"), ("casa", "c4sa")])
def test_analyze_pair_rejects_invalid_entries(pair):
    embedder = FakeEmbedder()
    with pytest.raises(EngineInputError, match="invalid entries"):
        analyze_pair(embedder, *pair)
    assert embedder.calls == []


@pytest.mark.parametrize("n", [2, 3, 7, 12])
def test_analyze_set_variable_size(n):
    words = [f"palabra{chr(97 + k)}" for k in range(n)]
    words = ["".join(ch for ch in w if ch.isalpha()) + "x" * k for k, w in enumerate(words)]
    embedder = FakeEmbedder()
    result = analyze_set(embedder, words)
    assert len(embedder.calls) == 1
    assert result.n_pairs == n * (n - 1) // 2
    assert result.distance_matrix.shape == (n, n)
    assert np.allclose(result.distance_matrix, result.distance_matrix.T)
    assert np.all(np.diag(result.distance_matrix) == 0)
    assert result.mean_distance == pytest.approx(np.mean([p.distance for p in result.pairs]), abs=1e-15)
    assert result.closest.distance == min(p.distance for p in result.pairs)
    assert result.most_distant.distance == max(p.distance for p in result.pairs)


def test_analyze_set_rejects_too_few_or_invalid():
    with pytest.raises(EngineInputError, match="at least two"):
        analyze_set(FakeEmbedder(), ["casa"])
    with pytest.raises(EngineInputError, match="position 2"):
        analyze_set(FakeEmbedder(), ["casa", "casa", "perro"])


def test_analyze_vectors_checks_shapes():
    with pytest.raises(EngineInputError):
        analyze_vectors(["a", "b", "c"], np.ones((2, 4)))


def test_analyze_vectors_known_values():
    result = analyze_vectors(["x", "y", "z"], np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]]))
    distances = {(p.word_i, p.word_j): p.distance for p in result.pairs}
    assert distances[("x", "y")] == pytest.approx(1.0, abs=1e-12)
    assert distances[("x", "z")] == pytest.approx(2.0, abs=1e-12)
    assert distances[("y", "z")] == pytest.approx(1.0, abs=1e-12)
    assert (result.most_distant.word_i, result.most_distant.word_j) == ("x", "z")


def test_dat7_selects_first_seven_eligible_in_order():
    entries = ["uno", "", "dos", "Uno", "tres", "cu4tro", "cuatro", "cinco", "seis", "siete", "ocho"]
    selection = select_dat7(entries)
    assert selection.words == ("uno", "dos", "tres", "cuatro", "cinco", "seis", "siete")
    assert selection.complete
    embedder = FakeEmbedder()
    result = analyze_dat7(embedder, entries)
    assert embedder.calls == [list(selection.words)]
    assert result.analysis.n_pairs == 21
    assert result.index == pytest.approx(result.analysis.mean_distance * 100.0, abs=0)
    assert 0.0 <= result.index <= 200.0


def test_dat7_with_fewer_than_seven_gives_no_index():
    embedder = FakeEmbedder()
    result = analyze_dat7(embedder, ["uno", "dos", "tres", "", "cuatro", "cinco", "seis"])
    assert result.index is None and result.analysis is None
    assert embedder.calls == []


def test_dat7_index_requires_seven_words():
    with pytest.raises(ValueError):
        dat7_index(analyze_vectors(["a", "b"], np.eye(2)))
