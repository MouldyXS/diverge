"""AnalysisService with synthetic embedders. No model.

Threads are coordinated with events and barriers; every wait has a timeout only as a safeguard against a hung test,
never as a performance criterion.
"""

import ast
import collections
import dataclasses
import json
import subprocess
import sys
import threading
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from app.engine import (EngineConfigError, EngineInputError, EngineValidationError, EntryReport, PairAnalysis, SetAnalysis,
                        analyze_pair, analyze_set)
from app.engine.errors import EngineError
from app.engine.validation import EntryCheck
from app.services import (DEFAULT_MAX_WORDS, SAFE_REASONS, UNRECOGNIZED_REASON, AnalysisBusy, AnalysisService,
                          EntriesRejected, EntryIssue, ModelRef, ServiceState, ServiceUnavailable, TooManyWords)
from app.services import analysis as service_module

WAIT = 10  # seconds; a safeguard only
BACKEND = Path(__file__).resolve().parents[1]


def description():
    return {
        "model_id": "fake/model", "revision": "declared-rev", "snapshot_revision": "snapshot-rev",
        "batch_size": 32, "expected_dimension": 8, "expected_modules": ("Transformer",),
        "modules": ["Transformer", "Pooling"], "versions": {"python": "3.12", "nested": {"items": [1, {"k": [2, 3]}]}},
    }


class FakeEmbedder:
    """`len(text) + 2` tokens against a 512-token limit; deterministic vectors; records calls and concurrency.

    `on_count` and `on_encode` run at the start of each call, to block or raise.
    """

    max_input_tokens = 512

    def __init__(self, info=None, on_count=None, on_encode=None):
        self.info = description() if info is None else info
        self.on_count, self.on_encode = on_count, on_encode
        self.calls = []  # (kind, texts, thread id)
        self.describe_calls = 0
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def _enter(self):
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

    def _leave(self):
        with self._guard:
            self.active -= 1

    def count_tokens(self, texts):
        self._enter()
        try:
            self.calls.append(("count", list(texts), threading.get_ident()))
            if self.on_count:
                self.on_count(texts)
            return [len(text) + 2 for text in texts]
        finally:
            self._leave()

    def encode(self, texts):
        self._enter()
        try:
            self.calls.append(("encode", list(texts), threading.get_ident()))
            if self.on_encode:
                self.on_encode(texts)
            rows = [np.random.default_rng(sum(ord(c) * (k + 1) for k, c in enumerate(t))).normal(size=8) for t in texts]
            return np.vstack(rows).astype(np.float32)
        finally:
            self._leave()

    def describe(self):
        self.describe_calls += 1
        return self.info

    def kinds(self):
        return [kind for kind, _, _ in self.calls]


class Gate:
    """Blocks a call until released, and tells the test when the call has entered."""

    def __init__(self, error=None):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.error = error

    def __call__(self, texts):
        self.entered.set()
        assert self.release.wait(WAIT), "gate never released"
        if self.error is not None:
            raise self.error


class SpyLock:
    def __init__(self):
        self.inner = threading.Lock()
        self.acquisitions = 0

    def acquire(self, blocking=True, timeout=-1):
        self.acquisitions += 1
        return self.inner.acquire(blocking, timeout)

    def release(self):
        self.inner.release()

    def locked(self):
        return self.inner.locked()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def words(n):
    return [chr(97 + k // 26) + chr(97 + k % 26) + "x" for k in range(n)]


def in_thread(function, *args):
    outcome = {}

    def run():
        try:
            outcome["result"] = function(*args)
        except BaseException as exc:  # noqa: BLE001 - recorded for the test
            outcome["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, outcome


def join(thread):
    thread.join(WAIT)
    assert not thread.is_alive(), "thread did not finish"


# A. Construction


def test_constructor_accepts_an_embedder_and_starts_ready_without_using_the_model():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    assert service.status() is ServiceState.READY
    assert embedder.describe_calls == 1 and embedder.calls == []  # no count_tokens, no encode
    assert service.model_info().limits.max_words == DEFAULT_MAX_WORDS == 32
    assert service.model_info().limits.max_input_tokens == 512


@pytest.mark.parametrize("candidate", [object(), "embedder", type("NoEncode", (), {"max_input_tokens": 512,
                                                                                    "count_tokens": lambda s, t: [],
                                                                                    "describe": lambda s: {}})()])
def test_constructor_rejects_objects_that_are_not_embedders(candidate):
    with pytest.raises(TypeError):
        AnalysisService(candidate)


@pytest.mark.parametrize("value, error", [(1, ValueError), (0, ValueError), (-3, ValueError), (True, TypeError),
                                          (False, TypeError), (2.0, TypeError), ("32", TypeError)])
def test_max_words_must_be_an_integer_of_at_least_two(value, error):
    with pytest.raises(error):
        AnalysisService(FakeEmbedder(), max_words=value)
    assert AnalysisService(FakeEmbedder(), max_words=2).model_info().limits.max_words == 2


@pytest.mark.parametrize("change", [
    lambda d: d.pop("model_id"),
    lambda d: d.update(model_id=""),
    lambda d: d.update(model_id=5),
    lambda d: d.pop("revision"),
    lambda d: d.update(revision=None),
    lambda d: d.update(snapshot_revision=7),
    lambda d: d.update(snapshot_revision=""),
    lambda d: d.update(extra=object()),
    lambda d: d.update(extra={1: "non-string key"}),
])
def test_incomplete_or_mistyped_metadata_prevents_construction(change):
    info = description()
    change(info)
    with pytest.raises(ValueError):
        AnalysisService(FakeEmbedder(info=info))


def test_describe_must_return_a_mapping_and_the_limit_must_be_valid():
    with pytest.raises(ValueError):
        AnalysisService(FakeEmbedder(info=["model_id"]))
    for bad in (0, True, None):
        embedder = FakeEmbedder()
        embedder.max_input_tokens = bad
        with pytest.raises(ValueError):
            AnalysisService(embedder)


def test_configuration_errors_of_the_embedder_prevent_construction():
    class Broken(FakeEmbedder):
        def describe(self):
            raise EngineConfigError("the pinned revision is not in the local cache")

    with pytest.raises(EngineConfigError):
        AnalysisService(Broken())


# B. Delegation


def test_analyze_pair_delegates_once_and_wraps_the_engine_object(monkeypatch):
    calls = []
    sentinel = PairAnalysis("a", "b", 0.25, 0.75)
    monkeypatch.setattr(service_module, "analyze_pair", lambda *args: calls.append(args) or sentinel)
    embedder = FakeEmbedder()
    result = AnalysisService(embedder).analyze_pair(" Casa", "perro")
    assert calls == [(embedder, " Casa", "perro")]
    assert result.analysis is sentinel
    assert result.model == ModelRef("fake/model", "declared-rev", "snapshot-rev")


def test_analyze_set_delegates_once_with_an_immutable_snapshot(monkeypatch):
    calls = []
    sentinel = object()
    monkeypatch.setattr(service_module, "analyze_set", lambda *args: calls.append(args) or sentinel)
    embedder = FakeEmbedder()
    entries = ["uno", "dos", "tres"]
    result = AnalysisService(embedder).analyze_set(entries)
    [(used, snapshot)] = calls
    assert used is embedder and snapshot == ("uno", "dos", "tres") and isinstance(snapshot, tuple)
    assert result.analysis is sentinel


def test_values_are_exactly_those_of_the_engine():
    service = AnalysisService(FakeEmbedder())
    pair = service.analyze_pair(" Casa", "PERRO").analysis
    direct = analyze_pair(FakeEmbedder(), " Casa", "PERRO")
    assert pair == direct and (pair.word_a, pair.word_b) == ("casa", "perro")
    assert pair.distance == 1.0 - pair.similarity
    entries = ["guerra", "paz", "noche", "sal"]
    result = service.analyze_set(entries).analysis
    reference = analyze_set(FakeEmbedder(), entries)
    assert isinstance(result, SetAnalysis)
    assert result.pairs == reference.pairs and result.mean_distance == reference.mean_distance
    assert np.array_equal(result.distance_matrix, reference.distance_matrix)
    assert (result.closest, result.most_distant) == (reference.closest, reference.most_distant)


def test_one_count_and_one_encode_per_analysis():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    service.analyze_pair("casa", "perro")
    service.analyze_set(["uno", "dos", "tres"])
    assert embedder.kinds() == ["count", "encode", "count", "encode"]


def test_pair_words_must_be_strings_before_admission():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    for args in ((1, "casa"), ("casa", None), (b"casa", "perro")):
        with pytest.raises(TypeError):
            service.analyze_pair(*args)
    assert embedder.calls == []


# C. Privacy of errors

ENTRIES = ["Murciélago", "dos palabras", "c4sa", "MURCIÉLAGO", "x" * 600]
TEXTS = ["Murciélago", "murciélago", "MURCIÉLAGO", "dos palabras", "c4sa", "x" * 600, "xxxxxxxx"]


def collect(obj, seen=None):
    """Every object reachable from an exception's own data: args, attributes, dataclass fields and containers."""
    seen = set() if seen is None else seen
    if id(obj) in seen:
        return []
    seen.add(id(obj))
    found = [obj]
    if isinstance(obj, BaseException):
        children = [obj.args, vars(obj), obj.__cause__, obj.__context__]
    elif dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        children = [getattr(obj, f.name) for f in dataclasses.fields(obj)]
    elif isinstance(obj, dict):
        children = list(obj.keys()) + list(obj.values())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        children = list(obj)
    else:
        children = []
    for child in children:
        found += collect(child, seen)
    return found


def assert_no_user_text(exc):
    objects = collect(exc)
    strings = [o for o in objects if isinstance(o, str)] + [str(exc), repr(exc)]
    strings += [repr(o) for o in objects if dataclasses.is_dataclass(o)]
    for text in TEXTS:
        assert not any(text in s for s in strings), text
    assert not any(isinstance(o, (EntryReport, EntryCheck, EngineError)) for o in objects)


def rejection(call):
    with pytest.raises(EntriesRejected) as info:
        call()
    return info.value


def test_rejected_entries_keep_positions_reasons_and_counts_but_no_text():
    embedder = FakeEmbedder()
    error = rejection(lambda: AnalysisService(embedder).analyze_set(ENTRIES))
    assert error.code == "invalid_entries"
    assert error.issues == (
        EntryIssue(2, ("multiple_words",), 14, 512),
        EntryIssue(3, ("digit_or_symbol",), 6, 512),
        EntryIssue(4, ("duplicate",), 12, 512),
        EntryIssue(5, ("exceeds_model_context",), 602, 512),
    )
    assert all(reason in SAFE_REASONS for issue in error.issues for reason in issue.reasons)
    assert error.__cause__ is None and error.__context__ is None and not error.__suppress_context__
    assert_no_user_text(error)
    assert embedder.kinds() == ["count"]  # rejected before encode


def test_pair_rejection_and_too_few_words_are_also_free_of_text():
    error = rejection(lambda: AnalysisService(FakeEmbedder()).analyze_pair("Murciélago", "MURCIÉLAGO"))
    assert error.code == "invalid_entries" and error.issues == (EntryIssue(2, ("duplicate",), 12, 512),)
    assert_no_user_text(error)
    error = rejection(lambda: AnalysisService(FakeEmbedder()).analyze_set(["Murciélago"]))
    assert error.code == "too_few_words" and error.issues == ()
    assert error.__context__ is None
    assert_no_user_text(error)


def test_unknown_engine_reasons_and_problems_are_replaced_by_safe_codes(monkeypatch):
    report = EntryReport(1, "Murciélago", "murciélago", ("murciélago_reason", "empty"), 12, 512)

    def raising(embedder, entries):
        raise EngineValidationError("invalid entries: position 1 'Murciélago'", entries=(report,), problem="Murciélago")

    monkeypatch.setattr(service_module, "analyze_set", raising)
    error = rejection(lambda: AnalysisService(FakeEmbedder()).analyze_set(["Murciélago", "perro"]))
    assert error.code == "invalid_entries"
    assert error.issues == (EntryIssue(1, (UNRECOGNIZED_REASON, "empty"), 12, 512),)
    assert error.__cause__ is None and error.__context__ is None
    assert_no_user_text(error)


def test_entry_issue_accepts_only_safe_codes_and_numbers():
    for bad in [dict(position=0), dict(position=True), dict(reasons=("murciélago",)), dict(reasons=()),
                dict(reasons=["empty"]), dict(tokens=-1), dict(max_tokens="512")]:
        fields = dict(position=1, reasons=("empty",), tokens=None, max_tokens=None) | bad
        with pytest.raises(ValueError):
            EntryIssue(**fields)


def test_a_validation_response_can_be_built_without_the_text():
    error = rejection(lambda: AnalysisService(FakeEmbedder()).analyze_set(ENTRIES))
    body = json.dumps({"code": error.code, "details": [dataclasses.asdict(issue) for issue in error.issues]})
    assert '"position": 5' in body and '"tokens": 602' in body
    assert not any(text in body for text in TEXTS)


# D. State


def test_engine_config_error_fails_the_service_and_propagates():
    failure = EngineConfigError("unexpected embeddings: shape (2, 3)")
    embedder = FakeEmbedder(on_encode=lambda texts: (_ for _ in ()).throw(failure))
    service = AnalysisService(embedder)
    with pytest.raises(EngineConfigError) as info:
        service.analyze_pair("casa", "perro")
    assert info.value is failure
    assert service.status() is ServiceState.FAILED
    with pytest.raises(ServiceUnavailable) as info:
        service.analyze_set(["uno", "dos"])
    assert info.value.state is ServiceState.FAILED and info.value.code == "service_unavailable"
    assert service.model_info().ref.model_id == "fake/model"
    assert embedder.kinds() == ["count", "encode"]  # the rejected request never reached the engine


def test_config_error_while_counting_also_fails_the_service():
    def broken(texts):
        raise EngineConfigError("the tokenizer failed")

    service = AnalysisService(FakeEmbedder(on_count=broken))
    with pytest.raises(EngineConfigError):
        service.analyze_pair("casa", "perro")
    assert service.status() is ServiceState.FAILED


@pytest.mark.parametrize("error", [RuntimeError("boom"), EngineInputError("zero vector"), TypeError("bad"),
                                   MemoryError(), KeyboardInterrupt()])
def test_other_errors_do_not_change_the_state(error):
    raised = []

    def once(texts):
        if not raised:
            raised.append(True)
            raise error

    service = AnalysisService(FakeEmbedder(on_encode=once))
    with pytest.raises(type(error)):
        service.analyze_pair("casa", "perro")
    assert service.status() is ServiceState.READY
    assert service.analyze_pair("casa", "perro").analysis.word_a == "casa"


def test_validation_errors_do_not_change_the_state():
    service = AnalysisService(FakeEmbedder())
    rejection(lambda: service.analyze_set(ENTRIES))
    assert service.status() is ServiceState.READY


def test_close_stops_ready_and_failed_services_and_is_idempotent():
    service = AnalysisService(FakeEmbedder())
    service.close()
    assert service.status() is ServiceState.STOPPING
    service.close()
    assert service.status() is ServiceState.STOPPING
    with pytest.raises(ServiceUnavailable) as info:
        service.analyze_pair("casa", "perro")
    assert info.value.state is ServiceState.STOPPING
    assert service.model_info().limits.max_words == 32

    failing = AnalysisService(FakeEmbedder(on_encode=lambda t: (_ for _ in ()).throw(EngineConfigError("x"))))
    with pytest.raises(EngineConfigError):
        failing.analyze_pair("casa", "perro")
    assert failing.status() is ServiceState.FAILED
    failing.close()
    assert failing.status() is ServiceState.STOPPING
    assert failing.model_info().ref.declared_revision == "declared-rev"


# E. Concurrency


def test_a_second_analysis_is_rejected_while_one_is_encoding():
    gate = Gate()
    service = AnalysisService(FakeEmbedder(on_encode=gate))
    thread, outcome = in_thread(service.analyze_pair, "casa", "perro")
    assert gate.entered.wait(WAIT)
    with pytest.raises(AnalysisBusy) as info:
        service.analyze_set(["uno", "dos"])
    assert info.value.code == "analysis_busy"
    assert service.status() is ServiceState.READY and service.model_info() is not None  # reads never wait
    gate.release.set()
    join(thread)
    assert outcome["result"].analysis.word_a == "casa"
    gate.entered.clear()
    assert service.analyze_set(["uno", "dos"]).analysis.n_pairs == 1


def test_the_exclusive_section_covers_token_counting():
    gate = Gate()
    embedder = FakeEmbedder(on_count=gate)
    service = AnalysisService(embedder)
    thread, outcome = in_thread(service.analyze_pair, "casa", "perro")
    assert gate.entered.wait(WAIT)
    with pytest.raises(AnalysisBusy):
        service.analyze_pair("sol", "luna")
    gate.release.set()
    join(thread)
    assert "result" in outcome
    assert [texts for kind, texts, _ in embedder.calls] == [["casa", "perro"], ["casa", "perro"]]


def test_counting_and_encoding_never_interleave_between_requests():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    barrier = threading.Barrier(8)
    done = []

    def worker(k):
        barrier.wait(WAIT)
        while True:
            try:
                service.analyze_set([f"{chr(97 + k)}uno", f"{chr(97 + k)}dos"])
                done.append(k)
                return
            except AnalysisBusy:
                pass

    threads = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        join(thread)
    assert sorted(done) == list(range(8))
    assert embedder.max_active == 1
    calls = embedder.calls
    assert len(calls) == 16
    for count, encode in zip(calls[::2], calls[1::2]):  # each count is followed by the encode of the same request
        assert (count[0], encode[0]) == ("count", "encode")
        assert count[1] == encode[1] and count[2] == encode[2]


@pytest.mark.parametrize("hook", ["on_count", "on_encode"])
@pytest.mark.parametrize("error", [RuntimeError("boom"), EngineInputError("x"), MemoryError(), EngineConfigError("x")])
def test_the_lock_is_released_after_any_exception(hook, error):
    embedder = FakeEmbedder(**{hook: lambda texts: (_ for _ in ()).throw(error)})
    service = AnalysisService(embedder)
    # The engine reports any failure of count_tokens other than its own errors as EngineConfigError (length.py).
    expected = EngineConfigError if hook == "on_count" and not isinstance(error, EngineError) else type(error)
    with pytest.raises(expected):
        service.analyze_pair("casa", "perro")
    assert not service._analysis_lock.locked() and not service._state_lock.locked()
    setattr(embedder, hook, None)
    if expected is EngineConfigError:
        assert service.status() is ServiceState.FAILED
    else:
        assert service.analyze_pair("casa", "perro").analysis.word_b == "perro"


def test_the_lock_is_released_after_a_rejection():
    service = AnalysisService(FakeEmbedder())
    rejection(lambda: service.analyze_set(ENTRIES))
    assert not service._analysis_lock.locked()
    assert service.analyze_set(["uno", "dos"]).analysis.n_pairs == 1


def test_an_admitted_analysis_finishes_during_close_and_new_ones_are_unavailable():
    gate = Gate()
    service = AnalysisService(FakeEmbedder(on_encode=gate))
    thread, outcome = in_thread(service.analyze_set, ["uno", "dos", "tres"])
    assert gate.entered.wait(WAIT)
    service.close()  # does not wait for the analysis
    assert service.status() is ServiceState.STOPPING
    with pytest.raises(ServiceUnavailable) as info:  # not AnalysisBusy, although the engine is busy
        service.analyze_pair("casa", "perro")
    assert info.value.state is ServiceState.STOPPING
    gate.release.set()
    join(thread)
    assert outcome["result"].analysis.n_pairs == 3
    assert service.status() is ServiceState.STOPPING


def test_eight_simultaneous_requests_give_one_success_and_seven_busy():
    gate = Gate()
    embedder = FakeEmbedder(on_encode=gate)
    service = AnalysisService(embedder)
    barrier = threading.Barrier(8)
    results = []
    finished = threading.Condition()

    def worker(k):
        barrier.wait(WAIT)
        try:
            service.analyze_pair(f"{chr(97 + k)}casa", f"{chr(97 + k)}perro")
            outcome = "ok"
        except AnalysisBusy:
            outcome = "busy"
        with finished:
            results.append(outcome)
            finished.notify_all()

    threads = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(8)]
    for thread in threads:
        thread.start()
    assert gate.entered.wait(WAIT)
    with finished:
        assert finished.wait_for(lambda: len(results) == 7, WAIT)
    assert results == ["busy"] * 7  # all rejected while the admitted one is still inside the engine
    gate.release.set()
    for thread in threads:
        join(thread)
    assert sorted(results) == ["busy"] * 7 + ["ok"]
    assert embedder.max_active == 1 and embedder.kinds() == ["count", "encode"]


def test_a_failure_after_close_leaves_the_service_stopping():
    gate = Gate(error=EngineConfigError("unexpected embeddings"))
    service = AnalysisService(FakeEmbedder(on_encode=gate))
    thread, outcome = in_thread(service.analyze_pair, "casa", "perro")
    assert gate.entered.wait(WAIT)
    service.close()
    gate.release.set()
    join(thread)
    assert isinstance(outcome["error"], EngineConfigError)
    assert service.status() is ServiceState.STOPPING  # never overwritten by FAILED
    assert not service._analysis_lock.locked()


# F. Inputs and limits


@pytest.mark.parametrize("value", ["casa", b"casa", bytearray(b"casa"), {"uno", "dos"}, np.array(["uno", "dos"]),
                                   {"uno": 1, "dos": 2}, (w for w in ["uno", "dos"])])
def test_analyze_set_rejects_non_sequences_and_single_strings(value):
    embedder = FakeEmbedder()
    with pytest.raises(TypeError):
        AnalysisService(embedder).analyze_set(value)
    assert embedder.calls == []


def test_supported_sequences_are_accepted():
    service = AnalysisService(FakeEmbedder())
    for value in (["uno", "dos"], ("uno", "dos"), collections.deque(["uno", "dos"])):
        assert service.analyze_set(value).analysis.words == ("uno", "dos")
    with pytest.raises(TypeError, match="every word"):  # a range is a sequence, but not of strings
        service.analyze_set(range(3))


def test_thirty_two_entries_are_accepted():
    result = AnalysisService(FakeEmbedder()).analyze_set(words(32))
    assert result.analysis.n_pairs == 496


def test_thirty_three_entries_are_rejected_before_counting_and_without_any_lock():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    service._state_lock, service._analysis_lock = SpyLock(), SpyLock()
    with pytest.raises(TooManyWords) as info:
        service.analyze_set(words(33))
    assert (info.value.max_words, info.value.received_at_least, info.value.code) == (32, 33, "too_many_words")
    assert embedder.calls == []
    assert service._state_lock.acquisitions == 0 and service._analysis_lock.acquisitions == 0


def test_p0_invalid_entries_count_for_the_limit():
    embedder = FakeEmbedder()
    with pytest.raises(TooManyWords):
        AnalysisService(embedder).analyze_set(words(31) + ["", "dos palabras"])
    assert embedder.calls == []


def test_received_at_least_is_a_lower_bound():
    with pytest.raises(TooManyWords) as info:
        AnalysisService(FakeEmbedder()).analyze_set(words(40))
    assert info.value.received_at_least == 33 <= 40
    with pytest.raises(TooManyWords) as info:
        AnalysisService(FakeEmbedder(), max_words=5).analyze_set(words(10))
    assert (info.value.max_words, info.value.received_at_least) == (5, 6)


def test_a_sequence_growing_during_the_copy_is_read_a_bounded_number_of_times():
    class Growing(Sequence):
        def __init__(self):
            self.items = ["uno", "dos"]
            self.reads = 0

        def __len__(self):
            return 2  # stale: the sequence grows while it is read

        def __getitem__(self, index):
            self.reads += 1
            self.items.append(f"w{'a' * len(self.items)}")
            return self.items[index]

    growing = Growing()
    embedder = FakeEmbedder()
    with pytest.raises(TooManyWords) as info:
        AnalysisService(embedder).analyze_set(growing)
    assert growing.reads == 33 and info.value.received_at_least == 33
    assert embedder.calls == []


def test_changes_to_the_list_after_the_copy_do_not_reach_the_engine():
    entries = ["uno", "dos", "tres"]

    def mutate(texts):
        entries[:] = ["otro"] * 40

    embedder = FakeEmbedder(on_count=mutate)
    result = AnalysisService(embedder).analyze_set(entries)
    assert result.analysis.words == ("uno", "dos", "tres")
    assert [texts for _, texts, _ in embedder.calls] == [["uno", "dos", "tres"]] * 2


# G. Metadata and isolation


def test_model_info_is_frozen_at_every_level():
    info = AnalysisService(FakeEmbedder()).model_info()
    description_ = info.description
    with pytest.raises(TypeError):
        description_["model_id"] = "other"
    with pytest.raises(TypeError):
        description_["versions"]["python"] = "3.13"
    with pytest.raises(TypeError):
        description_["versions"]["nested"]["items"][1]["k"] = []
    assert description_["modules"] == ("Transformer", "Pooling")
    assert description_["versions"]["nested"]["items"] == (1, {"k": (2, 3)})
    with pytest.raises(AttributeError):
        description_["modules"].append("Normalize")
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.ref.model_id = "other"
    assert not any(key.startswith("expected_") for key in description_)
    assert description_["batch_size"] == 32 and description_["snapshot_revision"] == "snapshot-rev"


def test_metadata_is_read_once_and_not_shared_with_the_embedder():
    embedder = FakeEmbedder()
    service = AnalysisService(embedder)
    embedder.info["model_id"] = "changed"
    embedder.info["versions"]["python"] = "changed"
    for _ in range(3):
        service.model_info()
        service.analyze_pair("casa", "perro")
    assert embedder.describe_calls == 1
    assert service.model_info().ref.model_id == "fake/model"
    assert service.model_info().description["versions"]["python"] == "3.12"


def test_declared_and_snapshot_revisions_stay_apart():
    service = AnalysisService(FakeEmbedder())
    ref = service.model_info().ref
    assert (ref.declared_revision, ref.snapshot_revision) == ("declared-rev", "snapshot-rev")
    assert service.analyze_pair("casa", "perro").model is ref
    for change in (lambda d: d.pop("snapshot_revision"), lambda d: d.update(snapshot_revision=None)):
        info = description()
        change(info)
        ref = AnalysisService(FakeEmbedder(info=info)).model_info().ref
        assert ref.snapshot_revision is None and ref.declared_revision == "declared-rev"


FORBIDDEN = ("fastapi", "starlette", "pydantic", "uvicorn", "httpx2", "httpx", "torch", "sentence_transformers",
             "transformers", "huggingface_hub")


def test_importing_the_service_loads_no_http_library_and_no_torch():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import app.services; "
        f"print(','.join(sorted(m for m in sys.modules if m.split('.')[0] in {FORBIDDEN!r})))"
    )
    completed = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(BACKEND)], capture_output=True, text=True,
                               timeout=120)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == ""


def test_service_modules_import_no_http_library_and_no_torch():
    files = sorted((BACKEND / "app" / "services").glob("*.py"))
    assert {f.name for f in files} == {"__init__.py", "analysis.py", "errors.py", "interpretation.py"}  # + interpretation (3B.9)
    for file in files:
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name.split(".")[0] in FORBIDDEN for name in names), (file.name, names)
