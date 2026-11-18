"""DAT7 and the model context, with a synthetic embedder. No model.

Policy: the selection is the first seven P0-eligible entries in entry order (P0-invalid entries are skipped, as
historically). If a selected entry is above the context limit, the whole request is rejected before encoding: the
entry is neither truncated nor skipped, and no later entry replaces it. Entries after the selection play no part.
"""

import numpy as np
import pytest

from app.engine import (EXCEEDS_MODEL_CONTEXT, EngineInputError, EngineValidationError, analyze_dat7, analyze_vectors,
                        dat7_index, select_dat7)


class SpyEmbedder:
    """`len(text) + 2` tokens (two special tokens) against a 512-token limit; records every call."""

    max_input_tokens = 512

    def __init__(self) -> None:
        self.count_calls: list[list[str]] = []
        self.encode_calls: list[list[str]] = []

    def count_tokens(self, texts):
        self.count_calls.append(list(texts))
        return [len(text) + 2 for text in texts]

    def encode(self, texts):
        self.encode_calls.append(list(texts))
        rows = [np.random.default_rng(sum(ord(c) * (k + 1) for k, c in enumerate(t))).normal(size=8) for t in texts]
        return np.vstack(rows).astype(np.float32)

    def describe(self):
        return {"model_id": "fake"}


AT_LIMIT = "q" * 510  # 512 tokens: accepted
OVER_LIMIT = "q" * 511  # 513 tokens: rejected
VERY_LONG = "z" * 698  # 700 tokens
SEVEN = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete"]


def expected_index(words, embedder):
    """The unchanged DAT7 computation on the given words, with a fresh embedder."""
    return dat7_index(analyze_vectors(words, embedder.encode(list(words))))


def assert_rejected(entries, position, tokens=513):
    embedder = SpyEmbedder()
    with pytest.raises(EngineValidationError) as info:
        analyze_dat7(embedder, entries)
    assert embedder.encode_calls == []  # nothing encoded: no partial result
    assert len(embedder.count_calls) == 1
    error = info.value
    assert isinstance(error, EngineInputError)
    assert error.problem == EngineValidationError.INVALID_ENTRIES
    assert [r.position for r in error.entries] == list(range(1, len(entries) + 1))  # one report per entry, in order
    [long_entry] = [r for r in error.entries if EXCEEDS_MODEL_CONTEXT in r.reasons]
    assert (long_entry.position, long_entry.tokens, long_entry.max_tokens) == (position, tokens, 512)
    assert f"position {position}" in str(error)
    return embedder, error


def test_seven_normal_entries_are_computed_as_before():
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, SEVEN)
    assert result.selection.words == tuple(SEVEN)
    assert embedder.count_calls == [SEVEN] and embedder.encode_calls == [SEVEN]
    assert result.analysis.n_pairs == 21
    assert result.index == expected_index(SEVEN, SpyEmbedder())
    assert result.index == pytest.approx(result.analysis.mean_distance * 100.0, abs=0)
    # Same selection as the P0-only selection (historical rule).
    assert select_dat7(SEVEN).words == result.selection.words


def test_entry_of_exactly_512_tokens_is_accepted():
    entries = ["uno", "dos", AT_LIMIT, "tres", "cuatro", "cinco", "seis"]
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, entries)
    assert result.selection.words == tuple(entries)
    assert result.selection.checks[2].tokens == 512 and result.selection.checks[2].reasons == ()
    assert embedder.encode_calls == [entries]
    assert result.index is not None


def test_513_tokens_in_the_first_selected_position_is_rejected():
    assert_rejected([OVER_LIMIT] + SEVEN, position=1)


def test_513_tokens_in_a_middle_position_is_rejected():
    assert_rejected(SEVEN[:3] + [OVER_LIMIT] + SEVEN[3:], position=4)


def test_513_tokens_in_the_seventh_selected_position_is_rejected():
    # Two P0-invalid entries first, so the seventh selected entry is at position 9; a valid 8th word follows.
    entries = ["", "dos palabras"] + SEVEN[:6] + [OVER_LIMIT, "siete"]
    embedder, error = assert_rejected(entries, position=9)
    assert embedder.count_calls == [SEVEN[:6] + [OVER_LIMIT]]  # "siete" is not used as a replacement, nor counted
    assert error.entries[0].reasons == ("empty",) and error.entries[1].reasons == ("multiple_words",)


def test_p0_invalid_entries_before_seven_are_still_skipped():
    entries = ["uno", "", "dos", "Uno", "tr3s", "tres", "cuatro", "cinco", "seis", "siete", "ocho"]
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, entries)
    assert result.selection.words == tuple(SEVEN)
    assert [r.reasons for r in result.selection.checks[:5]] == [(), ("empty",), (), ("duplicate",), ("digit_or_symbol",)]
    assert embedder.encode_calls == [SEVEN]
    assert result.index == expected_index(SEVEN, SpyEmbedder())


def test_long_entry_after_the_selection_is_ignored():
    for late in (OVER_LIMIT, VERY_LONG):
        embedder = SpyEmbedder()
        result = analyze_dat7(embedder, SEVEN + [late, "ocho"])
        assert result.selection.words == tuple(SEVEN)
        assert embedder.count_calls == [SEVEN]  # entries after the selection are not counted
        assert result.selection.checks[7].reasons == () and result.selection.checks[7].tokens is None
        assert result.index == expected_index(SEVEN, SpyEmbedder())


def test_p0_invalid_entry_after_the_selection_does_not_change_the_result():
    plain = analyze_dat7(SpyEmbedder(), SEVEN)
    embedder = SpyEmbedder()
    later = analyze_dat7(embedder, SEVEN + ["", "c4sa", "Uno", "dos palabras"])
    assert later.selection.words == plain.selection.words
    assert later.index == plain.index
    assert np.array_equal(later.analysis.distance_matrix, plain.analysis.distance_matrix)
    assert embedder.count_calls == [SEVEN] and embedder.encode_calls == [SEVEN]


def test_rejected_request_returns_no_index_or_partial_result():
    embedder = SpyEmbedder()
    result = None
    with pytest.raises(EngineValidationError):
        result = analyze_dat7(embedder, SEVEN[:2] + [OVER_LIMIT] + SEVEN[2:])
    assert result is None and embedder.encode_calls == []
    with pytest.raises(EngineValidationError):
        select_dat7(SEVEN[:2] + [OVER_LIMIT] + SEVEN[2:], SpyEmbedder())  # the selection itself refuses


def test_rejection_also_applies_with_fewer_than_seven_eligible():
    # The long entry appears before seven are selected, so the request is rejected rather than given no index.
    assert_rejected(SEVEN[:3] + [OVER_LIMIT] + ["", "cuatro"], position=4)
    # Without a long entry, fewer than seven still gives no index and nothing is encoded, as before.
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, SEVEN[:6])
    assert result.index is None and result.analysis is None and embedder.encode_calls == []


def test_p0_invalid_long_entry_is_skipped_by_p0_and_never_counted():
    long_invalid = OVER_LIMIT + "1"  # long, but already invalid by P0 (digit)
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, [long_invalid] + SEVEN)
    assert result.selection.checks[0].reasons == ("digit_or_symbol",) and result.selection.checks[0].tokens is None
    assert embedder.count_calls == [SEVEN] and result.selection.words == tuple(SEVEN)


def test_selected_words_keep_the_original_order():
    entries = ["siete", "", "uno", "cinco", "dos", "Siete", "tres", "seis", "cuatro", "ocho"]
    embedder = SpyEmbedder()
    result = analyze_dat7(embedder, entries)
    expected = ["siete", "uno", "cinco", "dos", "tres", "seis", "cuatro"]
    assert result.selection.words == tuple(expected)
    assert embedder.count_calls == [expected] and embedder.encode_calls == [expected]
    assert result.analysis.words == tuple(expected)
