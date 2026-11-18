"""Descriptive interpretation of a set analysis. Pure numbers: no model, no HTTP."""

import copy
import dataclasses
import itertools
import json
import random
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from app.engine import SetAnalysis, analyze_set, analyze_vectors
from app.engine.analysis import PairScore
from app.services import (AnalysisService, InterpretationError, PairRef, SetInterpretation, SetResult, interpret_set)
from app.services import interpretation as module
from app.services.analysis import ModelRef

BACKEND = Path(__file__).resolve().parents[1]
REF = ModelRef("fake/model", "declared-rev", "snapshot-rev")


def make_result(distances, n=None, words=None) -> SetResult:
    """A SetResult with exactly the given distances (pairs in combinations order), built like the engine builds it."""
    n = n or next(k for k in range(2, 80) if k * (k - 1) // 2 == len(distances))
    words = tuple(words or [f"w{k}" for k in range(n)])
    pairs = tuple(PairScore(i, j, words[i], words[j], 1.0 - d, float(d))
                  for (i, j), d in zip(itertools.combinations(range(n), 2), distances))
    order = np.argsort(np.array([p.distance for p in pairs]), kind="stable")  # the engine's rule
    analysis = SetAnalysis(words=words, pairs=pairs, distance_matrix=np.zeros((n, n)),
                           mean_distance=float(np.mean([p.distance for p in pairs])),
                           closest=pairs[int(order[0])], most_distant=pairs[int(order[-1])])
    return SetResult(analysis=analysis, model=REF)


TEN = [0.05, 0.18, 0.20, 0.26, 0.30, 0.31, 0.33, 0.34, 0.35, 0.36]  # 5 concepts; illustrative values


# Determinism, statistics and contract


def test_the_statistics_of_a_five_concept_set():
    result = make_result(TEN)
    it = interpret_set(result)
    assert (it.version, it.precision_decimals, it.n_pairs) == (1, 4, 10)
    assert (it.min_distance, it.max_distance) == (0.05, 0.36)
    assert it.range == pytest.approx(0.31, abs=1e-15)
    assert (it.n_above_mean, it.n_below_mean, it.n_at_mean) == (6, 4, 0)  # mean 0.268
    assert it.min_pairs == (PairRef(0, 1),) and it.max_pairs == (PairRef(3, 4),)
    assert (it.n_min_pairs, it.n_max_pairs) == (1, 1)
    assert it.flags == () and it.notes == ("relative_to_this_set", "no_reference_distribution", "mean_is_experimental")


def test_deterministic_and_the_result_is_not_modified():
    result = make_result(TEN)
    before = copy.deepcopy(result.analysis.pairs), result.analysis.mean_distance, result.analysis.closest
    outputs = {interpret_set(result) for _ in range(100)}
    assert len(outputs) == 1
    assert (result.analysis.pairs, result.analysis.mean_distance, result.analysis.closest) == before


def test_the_output_is_immutable_and_has_no_text_fields():
    it = interpret_set(make_result(TEN))
    with pytest.raises(dataclasses.FrozenInstanceError):
        it.n_pairs = 1
    assert not any(isinstance(value, str) for value in dataclasses.asdict(it).values())  # codes only in flags and notes
    assert all(isinstance(code, str) and code.isidentifier() for code in it.flags + it.notes)


def test_pairs_are_referenced_by_index_and_words_are_never_copied():
    result = make_result(TEN, words=["PRIVATE_A", "PRIVATE_B", "PRIVATE_C", "PRIVATE_D", "PRIVATE_E"])
    assert "PRIVATE" not in repr(interpret_set(result))


# Extremes and ties


@pytest.mark.parametrize("seed", range(40))
def test_the_first_listed_extremes_are_the_engines(seed):
    rng = random.Random(seed)
    n = rng.choice([2, 3, 5, 8, 12, 32])
    pool = [round(rng.random() * 0.5, rng.choice([2, 3, 4, 6])) for _ in range(6)]  # many exact ties
    distances = [rng.choice(pool) for _ in range(n * (n - 1) // 2)]
    result = make_result(distances)
    it = interpret_set(result)
    analysis = result.analysis
    assert (it.min_pairs[0].i, it.min_pairs[0].j) == (analysis.closest.i, analysis.closest.j)
    assert (it.max_pairs[0].i, it.max_pairs[0].j) == (analysis.most_distant.i, analysis.most_distant.j)
    assert it.min_distance == analysis.closest.distance and it.max_distance == analysis.most_distant.distance


def test_exact_ties_at_the_minimum_and_the_maximum_follow_the_engines_order():
    #           (0,1)  (0,2)  (0,3)  (1,2)  (1,3)  (2,3)
    result = make_result([0.20, 0.30, 0.20, 0.30, 0.25, 0.20])
    it = interpret_set(result)
    assert it.min_pairs == (PairRef(0, 1), PairRef(0, 3), PairRef(2, 3)) and it.n_min_pairs == 3
    assert result.analysis.closest.i == 0 and result.analysis.closest.j == 1  # the first of the tied minima
    assert it.max_pairs == (PairRef(1, 2), PairRef(0, 2)) and it.n_max_pairs == 2  # the last tied maximum comes first
    assert (result.analysis.most_distant.i, result.analysis.most_distant.j) == (1, 2)
    assert {"tie_at_min", "exact_tie_at_min", "tie_at_max", "exact_tie_at_max"} <= set(it.flags)
    assert "all_equal_at_precision" not in it.flags


def test_equal_at_four_decimals_but_not_exactly_equal():
    result = make_result([0.18151, 0.18149, 0.30, 0.31, 0.32, 0.33])
    it = interpret_set(result)
    assert it.n_min_pairs == 2
    assert [(p.i, p.j) for p in it.min_pairs] == [(0, 2), (0, 1)]  # the exact minimum (0.18149) is listed first
    assert "tie_at_min" in it.flags and "exact_tie_at_min" not in it.flags  # tied at the displayed value, not exactly
    assert module.quantize(0.18151) == module.quantize(0.18149) == Decimal("0.1815")


def test_distances_that_differ_at_the_fourth_decimal_do_not_tie():
    it = interpret_set(make_result([0.18149, 0.18160, 0.30, 0.31, 0.32, 0.33]))
    assert it.n_min_pairs == 1 and "tie_at_min" not in it.flags


def test_a_tie_at_the_maximum_is_independent_of_the_minimum():
    it = interpret_set(make_result([0.10, 0.30, 0.30, 0.25, 0.26, 0.27]))
    assert "tie_at_max" in it.flags and "tie_at_min" not in it.flags and it.n_max_pairs == 2


# Edge cases


def test_two_concepts_and_one_pair():
    it = interpret_set(make_result([0.18]))
    assert it.flags == ("single_pair",) and it.n_pairs == 1
    assert it.min_distance == it.max_distance == 0.18 and it.range == 0.0
    assert (it.n_above_mean, it.n_below_mean, it.n_at_mean) == (0, 0, 1)
    assert it.min_pairs == it.max_pairs == (PairRef(0, 1),)


def test_all_distances_equal():
    it = interpret_set(make_result([0.25] * 6))
    assert it.flags == ("all_equal_at_precision", "all_exactly_equal", "tie_at_min", "exact_tie_at_min", "tie_at_max",
                        "exact_tie_at_max")
    assert (it.n_above_mean, it.n_below_mean, it.n_at_mean) == (0, 0, 6) and it.range == 0.0
    assert it.n_min_pairs == it.n_max_pairs == 6


def test_all_equal_at_the_shown_precision_but_not_exactly():
    it = interpret_set(make_result([0.25001, 0.25002, 0.24999, 0.25003, 0.25, 0.24998]))
    assert "all_equal_at_precision" in it.flags and "all_exactly_equal" not in it.flags
    assert "exact_tie_at_min" not in it.flags and "exact_tie_at_max" not in it.flags
    assert (it.n_above_mean, it.n_below_mean, it.n_at_mean) == (0, 0, 6)


def test_a_mean_of_zero_needs_no_division():
    it = interpret_set(make_result([0.0, 0.0, 0.0]))
    assert it.range == 0.0 and "all_equal_at_precision" in it.flags and it.n_at_mean == 3


def test_a_slightly_negative_distance_from_float_error_is_handled():
    it = interpret_set(make_result([-2.2e-16, 0.0, 0.3]))  # cosine of identical vectors can exceed 1 by one ulp
    assert it.n_min_pairs == 2 and "tie_at_min" in it.flags


def test_counts_against_the_mean_use_the_displayed_values():
    # mean = 0.2; one pair is 0.20003 (equal to the mean at four decimals), the others are clearly above and below
    result = make_result([0.20003, 0.10, 0.30])
    it = interpret_set(result)
    assert (it.n_above_mean, it.n_below_mean, it.n_at_mean) == (1, 1, 1)


def test_thirty_two_concepts_keep_the_output_bounded():
    n = 32
    big = interpret_set(make_result([0.25] * (n * (n - 1) // 2)))
    assert big.n_pairs == 496 and big.n_min_pairs == big.n_max_pairs == 496
    assert len(big.min_pairs) == len(big.max_pairs) == 5  # at most five per extreme; the rest is only a count
    assert len(json.dumps(dataclasses.asdict(big))) < 1500
    rng = random.Random(1)
    varied = interpret_set(make_result([rng.random() * 0.4 for _ in range(496)]))
    assert varied.n_pairs == 496 and varied.n_above_mean + varied.n_below_mean + varied.n_at_mean == 496


@pytest.mark.parametrize("count", [1, 3, 6, 10, 45, 496])
def test_the_three_counts_always_add_up(count):
    rng = random.Random(count)
    it = interpret_set(make_result([round(rng.random(), 3) for _ in range(count)]))
    assert it.n_above_mean + it.n_below_mean + it.n_at_mean == count


# Rounding


GOLDEN = [  # (value, what Intl.NumberFormat shows with four decimals); produced with the same ICU rule as the interface
    ("0.00145", "0.0015"), ("0.00565", "0.0057"), ("0.00635", "0.0064"), ("0.00705", "0.0071"), ("0.00005", "0.0001"),
    ("0.00015", "0.0002"), ("0.00025", "0.0003"), ("0.18145", "0.1815"), ("0.18155", "0.1816"), ("0.18149", "0.1815"),
    ("0.18151", "0.1815"), ("0.18160", "0.1816"), ("0.30005", "0.3001"), ("0.34995", "0.3500"), ("0.34994999999999", "0.3499"),
    ("0.2", "0.2000"), ("0.2000000001", "0.2000"), ("0.19999999999", "0.2000"), ("0.12345", "0.1235"), ("0.12355", "0.1236"),
    ("0.99995", "1.0000"), ("1.00005", "1.0001"), ("1.5", "1.5000"), ("2", "2.0000"), ("0", "0.0000"), ("1e-05", "0.0000"),
    ("4.9999e-05", "0.0000"), ("5e-05", "0.0001"), ("0.00014999", "0.0001"), ("0.000149999999", "0.0001"),
    ("0.18148765432109876", "0.1815"), ("0.2987654321098766", "0.2988"),
]


@pytest.mark.parametrize("text, shown", GOLDEN)
def test_quantize_agrees_with_the_four_decimals_the_interface_shows(text, shown):
    assert f"{module.quantize(float(text)):.4f}" == shown


def test_python_round_would_disagree_in_boundary_cases_which_is_why_it_is_not_used():
    assert f"{round(0.00145, 4):.4f}" != "0.0015" and f"{module.quantize(0.00145):.4f}" == "0.0015"


def test_quantize_over_many_values_is_stable_and_monotonic():
    rng = random.Random(7)
    values = sorted(rng.random() * 0.5 for _ in range(20000))
    shown = [module.quantize(v) for v in values]
    assert shown == sorted(shown)  # a larger value never displays smaller
    assert all(abs(float(q) - v) <= 5.0000001e-5 for q, v in zip(shown, values))


# Invalid input


def broken(**changes):
    base = make_result([0.1, 0.2, 0.3])
    analysis = dataclasses.replace(base.analysis, **changes)
    return SetResult(analysis=analysis, model=REF)


def test_inconsistent_data_raises():
    ok = make_result([0.1, 0.2, 0.3])
    pairs = list(ok.analysis.pairs)
    cases = {
        "missing pair": broken(pairs=tuple(pairs[:2])),
        "duplicated pair": broken(pairs=(pairs[0], pairs[0], pairs[2])),
        "reversed indexes": broken(pairs=(dataclasses.replace(pairs[0], i=1, j=0), pairs[1], pairs[2])),
        "index out of range": broken(pairs=(dataclasses.replace(pairs[0], j=5), pairs[1], pairs[2])),
        "boolean index": broken(pairs=(dataclasses.replace(pairs[0], i=False), pairs[1], pairs[2])),
        "wrong closest": broken(closest=pairs[2]),
        "wrong most distant": broken(most_distant=pairs[0]),
        "one word": broken(words=("a",), pairs=()),
    }
    for name, result in cases.items():
        with pytest.raises(InterpretationError):
            interpret_set(result)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_raise(bad):
    ok = make_result([0.1, 0.2, 0.3])
    pairs = list(ok.analysis.pairs)
    with pytest.raises(InterpretationError):
        interpret_set(broken(pairs=(dataclasses.replace(pairs[0], distance=bad), pairs[1], pairs[2])))
    with pytest.raises(InterpretationError):
        interpret_set(broken(mean_distance=bad))


def test_something_that_is_not_a_set_result_raises():
    for bad in (None, object(), "text", 3):
        with pytest.raises(InterpretationError):
            interpret_set(bad)


def test_errors_never_carry_user_text():
    result = make_result([0.1, 0.2, 0.3], words=["PRIVATE_A", "PRIVATE_B", "PRIVATE_C"])
    with pytest.raises(InterpretationError) as info:
        interpret_set(broken(words=("PRIVATE_A",), pairs=()))
    assert "PRIVATE" not in str(info.value) and "PRIVATE" not in repr(info.value.args)
    assert result is not None


# Real engine objects


def test_it_describes_what_the_real_engine_returns():
    class Fake:
        max_input_tokens = 512

        def count_tokens(self, texts):
            return [len(t) + 2 for t in texts]

        def encode(self, texts):
            return np.vstack([np.random.default_rng(sum(ord(c) * (k + 1) for k, c in enumerate(t))).normal(size=8) for t in texts]).astype(np.float32)

        def describe(self):
            return {"model_id": "fake/model", "revision": "r"}

    result = AnalysisService(Fake()).analyze_set(["guerra", "paz", "noche", "martillo", "ciencia"])
    it = interpret_set(result)
    assert it.n_pairs == 10 and it.min_pairs[0] == PairRef(result.analysis.closest.i, result.analysis.closest.j)
    assert it.n_above_mean + it.n_below_mean + it.n_at_mean == 10
    assert isinstance(it, SetInterpretation)
    again = analyze_vectors(result.analysis.words, np.eye(5))  # a plain engine object also works through its SetResult
    assert interpret_set(SetResult(analysis=again, model=REF)).n_pairs == 10


# Isolation


def test_the_module_is_importable_without_http_libraries_or_torch():
    forbidden = ("fastapi", "starlette", "pydantic", "uvicorn", "httpx2", "httpx", "torch", "sentence_transformers",
                 "transformers", "huggingface_hub")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import app.services.interpretation; "
            f"print(','.join(sorted(m for m in sys.modules if m.split('.')[0] in {forbidden!r})))")
    completed = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(BACKEND)], capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == ""


def test_the_module_imports_only_the_standard_library_and_the_service_types():
    import ast

    tree = ast.parse((BACKEND / "app" / "services" / "interpretation.py").read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add(("." + (node.module or "")) if node.level else node.module.split(".")[0])
    assert roots <= {"__future__", "math", "dataclasses", "decimal", ".analysis"}, roots
