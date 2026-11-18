"""Model context with the real tokenizer of the local reference model. Marked `model`.

Checks the exact boundary (511, 512 and 513 tokens, special tokens included), that counted ids equal the ids of the
real preprocessing path up to the limit, that the preprocessing path would truncate a longer input, and that the
analysis rejects such an input before calling `encode`.
"""

import socket

import numpy as np
import pytest

from app.engine import (EXCEEDS_MODEL_CONTEXT, EngineValidationError, GraniteEmbedder, analyze_dat7, analyze_pair, analyze_set,
                        check_lengths)

pytestmark = pytest.mark.model

# Inputs found with this tokenizer during the 3B.1 review; the tests recount them rather than trust these values.
BOUNDARY = {511: ("ñ" * 508, "casa" * 509), 512: ("ñ" * 509, "casa" * 510), 513: ("ñ" * 510, "casa" * 511)}


@pytest.fixture(scope="module")
def no_network():
    attempts = []
    original = (socket.getaddrinfo, socket.create_connection, socket.socket.connect)

    def blocked(*args, **kwargs):
        attempts.append(repr(args[:2]))
        raise OSError("network disabled in model tests")

    socket.getaddrinfo, socket.create_connection, socket.socket.connect = blocked, blocked, blocked
    yield attempts
    socket.getaddrinfo, socket.create_connection, socket.socket.connect = original


@pytest.fixture(scope="module")
def embedder(no_network):
    return GraniteEmbedder()


class Spy:
    """Delegates everything to the real embedder and records every encode call."""

    def __init__(self, inner):
        self.inner = inner
        self.encode_calls = []

    @property
    def max_input_tokens(self):
        return self.inner.max_input_tokens

    def count_tokens(self, texts):
        return self.inner.count_tokens(texts)

    def encode(self, texts):
        self.encode_calls.append(list(texts))
        return self.inner.encode(texts)

    def describe(self):
        return self.inner.describe()


def raw_ids(embedder, text):
    return embedder.model.tokenizer(text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]


def preprocessed_ids(embedder, text):
    features = embedder.model.preprocess([text])
    mask = features["attention_mask"][0].bool()
    return features["input_ids"][0][mask].tolist()


def test_limit_is_the_effective_model_context(embedder):
    assert embedder.max_input_tokens == embedder.model.max_seq_length == embedder.model.tokenizer.model_max_length == 512


@pytest.mark.parametrize("tokens", [511, 512, 513])
def test_boundary_counts_include_special_tokens(embedder, tokens):
    tokenizer = embedder.model.tokenizer
    for text in BOUNDARY[tokens]:
        assert embedder.count_tokens([text]) == [tokens]
        ids = raw_ids(embedder, text)
        assert len(ids) == tokens
        assert ids[0] == tokenizer.cls_token_id and ids[-1] == tokenizer.sep_token_id


@pytest.mark.parametrize("tokens", [511, 512])
def test_counted_ids_equal_the_real_preprocessing_up_to_the_limit(embedder, tokens):
    for text in BOUNDARY[tokens]:
        assert raw_ids(embedder, text) == preprocessed_ids(embedder, text)


def test_preprocessing_would_truncate_513_tokens_silently(embedder):
    for text in BOUNDARY[513]:
        assert embedder.count_tokens([text]) == [513]
        truncated = preprocessed_ids(embedder, text)
        assert len(truncated) == 512 and truncated != raw_ids(embedder, text)
    # The truncation the engine now prevents: 513 tokens would embed exactly like 512 tokens.
    assert np.array_equal(embedder.encode([BOUNDARY[513][0]]), embedder.encode([BOUNDARY[512][0]]))


def test_check_lengths_marks_only_513(embedder):
    texts = [BOUNDARY[511][0], BOUNDARY[512][0], BOUNDARY[513][0]]
    assert [c.reasons for c in check_lengths(embedder, texts)] == [(), (), (EXCEEDS_MODEL_CONTEXT,)]


@pytest.mark.parametrize("tokens", [511, 512])
def test_inputs_within_the_limit_are_analyzed(embedder, tokens):
    spy = Spy(embedder)
    result = analyze_pair(spy, BOUNDARY[tokens][0], "casa")
    assert spy.encode_calls == [[BOUNDARY[tokens][0], "casa"]]
    assert np.isfinite(result.distance) and 0.0 <= result.distance <= 2.0


def test_dat7_boundary_with_the_real_tokenizer(embedder, no_network):
    words = ["perro", "nube", "martillo", "ciencia", "sal", "guitarra"]
    spy = Spy(embedder)
    accepted = analyze_dat7(spy, [BOUNDARY[512][0]] + words)
    assert accepted.selection.checks[0].tokens == 512 and spy.encode_calls == [[BOUNDARY[512][0]] + words]
    spy = Spy(embedder)
    with pytest.raises(EngineValidationError) as info:
        analyze_dat7(spy, [BOUNDARY[513][0]] + words + ["volcan"])
    assert spy.encode_calls == []  # neither truncated nor replaced by "volcan"
    [entry] = info.value.invalid
    assert (entry.position, entry.tokens, entry.max_tokens) == (1, 513, 512)
    late = "ñ" * 697
    assert embedder.count_tokens([late]) == [700]
    spy = Spy(embedder)
    result = analyze_dat7(spy, ["casa"] + words + [late])  # 700 tokens after the selection: no part in it
    assert result.index is not None and spy.encode_calls == [["casa"] + words]
    assert no_network == []


def test_513_tokens_rejected_before_encode(embedder, no_network):
    spy = Spy(embedder)
    with pytest.raises(EngineValidationError) as info:
        analyze_pair(spy, BOUNDARY[513][0], "casa")
    assert spy.encode_calls == []
    [entry] = info.value.invalid
    assert (entry.position, entry.reasons, entry.tokens, entry.max_tokens) == (1, (EXCEEDS_MODEL_CONTEXT,), 513, 512)
    with pytest.raises(EngineValidationError):
        analyze_set(spy, ["perro", BOUNDARY[513][1], "gato"])
    assert spy.encode_calls == []
    assert no_network == []
