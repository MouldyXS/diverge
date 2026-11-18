"""Model-context validation with synthetic embedders. No model.

The token count of each entry is checked once per analysis, before any encoding; an entry above the inclusive limit
gets `exceeds_model_context`, the whole request is rejected, and `encode` is never called.
"""

import numpy as np
import pytest

from app.engine import (EXCEEDS_MODEL_CONTEXT, EngineConfigError, EngineInputError, EngineValidationError, analyze_dat7,
                        analyze_pair, analyze_set, analyze_vectors, check_lengths, select_dat7, validate_entries)
from app.engine.validation import length as length_module


class TokenEmbedder:
    """Counts `len(text) + 2` tokens (two special tokens) against a small limit, and records every call."""

    def __init__(self, limit: int = 8, dimension: int = 6) -> None:
        self.limit = limit
        self.dimension = dimension
        self.count_calls: list[list[str]] = []
        self.encode_calls: list[list[str]] = []

    @property
    def max_input_tokens(self):
        return self.limit

    def count_tokens(self, texts):
        self.count_calls.append(list(texts))
        return [len(text) + 2 for text in texts]

    def encode(self, texts):
        self.encode_calls.append(list(texts))
        rows = [np.random.default_rng(sum(ord(c) * (k + 1) for k, c in enumerate(t))).normal(size=self.dimension) for t in texts]
        return np.vstack(rows).astype(np.float32)

    def describe(self):
        return {"model_id": "fake"}


# With limit 8: a 6-letter word is 8 tokens (accepted, at the limit), a 7-letter word is 9 tokens (rejected).
AT_LIMIT, OVER_LIMIT, UNDER_LIMIT = "abcdef", "abcdefg", "abcde"


def test_check_lengths_counts_in_order_with_special_tokens():
    embedder = TokenEmbedder()
    result = check_lengths(embedder, ["ab", "abcd", "a"])
    assert [r.tokens for r in result] == [4, 6, 3]  # len + 2 special tokens, in input order
    assert [r.position for r in result] == [1, 2, 3]
    assert all(r.max_tokens == 8 for r in result)
    assert embedder.count_calls == [["ab", "abcd", "a"]]  # one call for all texts


def test_limit_is_inclusive():
    embedder = TokenEmbedder()
    under, at, over = check_lengths(embedder, [UNDER_LIMIT, AT_LIMIT, OVER_LIMIT])
    assert (under.tokens, at.tokens, over.tokens) == (7, 8, 9)
    assert under.reasons == () and at.reasons == ()
    assert over.reasons == (EXCEEDS_MODEL_CONTEXT,)


def test_check_lengths_rejects_non_strings_and_handles_empty_lists():
    with pytest.raises(EngineInputError, match="string"):
        check_lengths(TokenEmbedder(), ["casa", 3])
    assert check_lengths(TokenEmbedder(), []) == []


def test_entry_at_limit_is_analyzed_and_encoded_once():
    embedder = TokenEmbedder()
    result = analyze_pair(embedder, AT_LIMIT, UNDER_LIMIT)
    assert (result.word_a, result.word_b) == (AT_LIMIT, UNDER_LIMIT)
    assert embedder.encode_calls == [[AT_LIMIT, UNDER_LIMIT]]
    assert len(embedder.count_calls) == 1


def test_entry_over_limit_is_rejected_before_encode():
    embedder = TokenEmbedder()
    with pytest.raises(EngineValidationError) as info:
        analyze_pair(embedder, OVER_LIMIT, UNDER_LIMIT)
    assert embedder.encode_calls == []  # no partial or full encoding
    error = info.value
    assert error.problem == "invalid_entries"
    assert [(e.position, e.reasons, e.tokens, e.max_tokens) for e in error.invalid] == [(1, (EXCEEDS_MODEL_CONTEXT,), 9, 8)]
    assert "invalid entries: position 1" in str(error)


def test_set_with_one_invalid_word_is_rejected_whole():
    embedder = TokenEmbedder()
    with pytest.raises(EngineValidationError) as info:
        analyze_set(embedder, ["ab", OVER_LIMIT, "cd", "ef"])
    assert embedder.encode_calls == []  # the valid words are not encoded either
    assert [e.position for e in info.value.entries] == [1, 2, 3, 4]  # every entry reported, in order
    assert [e.position for e in info.value.invalid] == [2]


def test_several_invalid_entries_keep_every_p0_reason_and_order():
    embedder = TokenEmbedder()
    entries = ["ab", "", "dos palabras", "c4sa", "Ab", "!", OVER_LIMIT, OVER_LIMIT.upper()]
    reports = validate_entries(entries, embedder)
    assert [r.reasons for r in reports] == [
        (),
        ("empty",),
        ("multiple_words", EXCEEDS_MODEL_CONTEXT),  # 12 letters + 2
        ("digit_or_symbol",),
        ("duplicate",),
        ("digit_or_symbol",),
        (EXCEEDS_MODEL_CONTEXT,),
        ("duplicate", EXCEEDS_MODEL_CONTEXT),  # P0 reasons first, then the context reason
    ]
    assert [r.normalized for r in reports][4] == "ab"
    with pytest.raises(EngineValidationError) as info:
        analyze_set(embedder, entries)
    assert [e.position for e in info.value.invalid] == [2, 3, 4, 5, 6, 7, 8]
    assert embedder.encode_calls == []


def test_p0_rules_alone_are_unchanged_without_embedder():
    reports = validate_entries(["perro", "", "Perro"])
    assert [r.reasons for r in reports] == [(), ("empty",), ("duplicate",)]
    assert all(r.tokens is None and r.max_tokens is None for r in reports)


def test_tokens_counted_on_the_normalized_text():
    embedder = TokenEmbedder()
    validate_entries(["  Casa ", "PERRO"], embedder)
    assert embedder.count_calls == [["casa", "perro"]]  # the text encode() would receive


def test_validation_runs_once_per_analysis(monkeypatch):
    calls = []
    original = length_module.check_entries

    def spy(entries):
        calls.append(list(entries))
        return original(entries)

    monkeypatch.setattr(length_module, "check_entries", spy)
    embedder = TokenEmbedder()
    analyze_set(embedder, ["ab", "cd", "ef"])
    assert len(calls) == 1 and len(embedder.count_calls) == 1 and len(embedder.encode_calls) == 1
    analyze_pair(embedder, "ab", "cd")
    assert len(calls) == 2 and len(embedder.count_calls) == 2 and len(embedder.encode_calls) == 2


def test_word_and_pair_order_is_preserved():
    embedder = TokenEmbedder()
    result = analyze_set(embedder, ["c", "A", "b"])
    assert result.words == ("c", "a", "b")
    assert [(p.word_i, p.word_j) for p in result.pairs] == [("c", "a"), ("c", "b"), ("a", "b")]


def test_too_few_words_is_a_validation_error():
    with pytest.raises(EngineValidationError, match="at least two") as info:
        analyze_set(TokenEmbedder(), ["ab"])
    assert info.value.problem == "too_few_words"


class FailingTokenizer(TokenEmbedder):
    def count_tokens(self, texts):
        raise RuntimeError("tokenizer broke")


class MalformedCounts(TokenEmbedder):
    def __init__(self, counts, **kwargs):
        super().__init__(**kwargs)
        self.counts = counts

    def count_tokens(self, texts):
        return self.counts


class BadLimit(TokenEmbedder):
    def __init__(self, limit):
        super().__init__()
        self.bad = limit

    @property
    def max_input_tokens(self):
        if isinstance(self.bad, Exception):
            raise self.bad
        return self.bad


@pytest.mark.parametrize("embedder", [
    FailingTokenizer(),
    MalformedCounts([3]),  # wrong number of counts
    MalformedCounts([3, "4"]),  # not an integer
    MalformedCounts([3, -1]),  # negative
    MalformedCounts([3, True]),  # bool is not a count
    BadLimit(0),
    BadLimit(None),
    BadLimit(True),
    BadLimit(AttributeError("no tokenizer")),
])
def test_tokenizer_or_limit_failures_are_configuration_errors_and_never_valid(embedder):
    with pytest.raises(EngineConfigError):
        analyze_pair(embedder, "ab", "cd")
    assert embedder.encode_calls == []


def test_vector_errors_are_not_validation_errors():
    with pytest.raises(EngineInputError) as info:
        analyze_vectors(["a", "b"], np.array([[1.0, np.nan], [0.0, 1.0]]))
    assert not isinstance(info.value, EngineValidationError)


def test_validation_error_is_still_an_engine_input_error():
    with pytest.raises(EngineInputError):
        analyze_pair(TokenEmbedder(), "", "ab")


def test_dat7_rejects_a_selected_entry_over_the_limit():
    # The DAT7 policy itself is covered in test_dat7_context.py.
    embedder = TokenEmbedder()
    with pytest.raises(EngineValidationError):
        analyze_dat7(embedder, ["a", OVER_LIMIT, "b", "c", "d", "e", "f", "g", "h"])
    assert len(embedder.count_calls) == 1 and embedder.encode_calls == []


def test_select_dat7_without_embedder_keeps_p0_only():
    selection = select_dat7(["a", OVER_LIMIT, "b", "c", "d", "e", "f"])
    assert selection.words == ("a", OVER_LIMIT, "b", "c", "d", "e", "f")
