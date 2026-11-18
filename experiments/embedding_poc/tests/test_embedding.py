"""Technical tests of the Granite embedding extraction (Phase 2a). No test looks at semantic relations.

Run from the repository root:
    .venv\\Scripts\\python.exe -m pytest experiments\\embedding_poc\\tests -q
The model must already be in the local Hugging Face cache (see experiments/embedding_poc/README.md).
"""

from __future__ import annotations

import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import embedding as emb  # noqa: E402


@pytest.fixture(scope="module")
def st():
    return emb.get_st()


@pytest.fixture(scope="module")
def explicit():
    return emb.get_explicit()


@pytest.fixture(scope="module")
def ref_vectors(st):
    return emb.encode_st(st, emb.TECH_INPUTS)


# ------------------------------------------------------------------------------------- load and shape
def test_cpu_build_and_device(st):
    assert torch.version.cuda is None and not torch.cuda.is_available()
    assert emb.pipeline_summary(st)["device"] == "cpu"
    assert emb.pipeline_summary(st)["parameter_dtype"] == "torch.float32"


def test_pipeline_follows_the_model_configuration(st):
    cfg = emb.describe_config()
    summary = emb.pipeline_summary(st)
    assert cfg["snapshot_revision_from_path"] == emb.REVISION
    assert cfg["architecture"] == ["XLMRobertaModel"]
    assert cfg["pooling_config"]["pooling_mode_cls_token"] is True
    assert not any(cfg["pooling_config"][k] for k in ("pooling_mode_mean_tokens", "pooling_mode_max_tokens", "pooling_mode_mean_sqrt_len_tokens"))
    assert cfg["modules_json"] == ["Transformer", "Pooling", "Normalize"]
    assert summary["modules"] == cfg["modules_json"]
    assert summary["pooling_mode"] == "cls"
    assert summary["has_normalize_module"] is True
    assert "flash" not in summary["attention_implementation"].lower()


def test_dimensionality_finite_and_not_null(ref_vectors):
    h = emb.health(ref_vectors)
    assert h["shape"] == [len(emb.TECH_INPUTS), emb.EXPECTED_DIM]
    assert h["all_finite"]
    assert h["null_vectors"] == 0


def test_l2_normalization(ref_vectors):
    norms = np.linalg.norm(ref_vectors.astype(np.float64), axis=1)
    assert np.abs(norms - 1).max() <= emb.NORM_ATOL


def test_normalization_is_applied_exactly_once(st):
    stages = emb.st_stages(st, emb.TECH_INPUTS)
    raw_norms = np.linalg.norm(stages["raw_cls"], axis=1)
    assert raw_norms.min() > 2.0, "pooled CLS vectors must not be unit vectors before the Normalize module"
    assert np.abs(np.linalg.norm(stages["normalized"], axis=1) - 1).max() <= emb.NORM_ATOL
    # encode() with its defaults is exactly modules 0, 1 and 2, not a fourth step
    assert np.abs(emb.encode_st(st, emb.TECH_INPUTS) - stages["normalized"]).max() <= emb.REPRO_ATOL
    # the pooled vector divided by its own norm is the final vector: no hidden second operation
    again = stages["raw_cls"] / np.linalg.norm(stages["raw_cls"], axis=1, keepdims=True)
    assert np.abs(again - stages["normalized"]).max() <= emb.IMPL_ATOL


# ---------------------------------------------------------------------------- reference vs explicit
def test_same_token_ids_in_both_paths(st, explicit):
    assert emb.st_stages(st, emb.TECH_INPUTS)["input_ids"] == explicit.token_ids(emb.TECH_INPUTS)


def test_explicit_path_matches_reference(st, explicit, ref_vectors):
    manual = explicit.encode(emb.TECH_INPUTS)
    result = emb.compare(ref_vectors, manual)
    assert result["shape_a"] == result["shape_b"] == [len(emb.TECH_INPUTS), emb.EXPECTED_DIM]
    assert result["min_cosine"] >= emb.COSINE_MIN
    assert result["max_abs_diff"] <= emb.IMPL_ATOL
    assert result["max_norm_deviation_a"] <= emb.NORM_ATOL and result["max_norm_deviation_b"] <= emb.NORM_ATOL


def test_pooled_cls_before_normalization_matches(st, explicit):
    a = emb.st_stages(st, emb.TECH_INPUTS)["raw_cls"].astype(np.float64)
    b = explicit.raw_cls(emb.TECH_INPUTS).astype(np.float64)
    relative = np.linalg.norm(a - b, axis=1) / np.linalg.norm(a, axis=1)
    assert relative.max() <= emb.IMPL_ATOL


def test_explicit_path_uses_the_first_token_not_the_mean(st, explicit):
    """Sensitivity check: a mean-pooled vector must NOT satisfy the tolerance, so the comparison can detect a wrong pooling."""
    enc = explicit.tokenizer(emb.TECH_INPUTS, padding=True, return_tensors="pt")
    with torch.inference_mode():
        hidden = explicit.model(**enc)[0]
        mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
        mean = torch.nn.functional.normalize((hidden * mask).sum(1) / mask.sum(1), dim=1).numpy()
    assert emb.compare(emb.encode_st(st, emb.TECH_INPUTS), mean)["min_cosine"] < emb.COSINE_MIN


# ---------------------------------------------------------------------------------- reproducibility
def test_repeated_input_gives_equivalent_embeddings(st, ref_vectors):
    assert np.abs(emb.encode_st(st, emb.TECH_INPUTS) - ref_vectors).max() <= emb.REPRO_ATOL
    twice = emb.encode_st(st, ["casa", "casa"])
    assert np.abs(twice[0] - twice[1]).max() <= emb.REPRO_ATOL


def test_batch_equals_individual_processing(st, ref_vectors):
    single = np.vstack([emb.encode_st(st, [t]) for t in emb.TECH_INPUTS])
    assert np.abs(single - ref_vectors).max() <= emb.REPRO_ATOL
    for batch_size in (1, 2, 5, 64):
        assert np.abs(emb.encode_st(st, emb.TECH_INPUTS, batch_size=batch_size) - ref_vectors).max() <= emb.REPRO_ATOL


def test_order_is_preserved(st, ref_vectors):
    reversed_out = emb.encode_st(st, emb.TECH_INPUTS[::-1])[::-1]
    assert np.abs(reversed_out - ref_vectors).max() <= emb.REPRO_ATOL
    # sensitivity: swapping two rows must be visible with this tolerance
    swapped = ref_vectors.copy()
    swapped[[0, 1]] = swapped[[1, 0]]
    assert np.abs(swapped - ref_vectors).max() > emb.IMPL_ATOL


def test_fresh_process_gives_the_same_embeddings(ref_vectors, tmp_path):
    out = tmp_path / "child.npy"
    code = ("import sys, numpy as np; sys.path.insert(0, sys.argv[1]); import embedding as e; "
            "np.save(sys.argv[2], e.encode_st(e.get_st(), e.TECH_INPUTS))")
    proc = subprocess.run([sys.executable, "-c", code, str(Path(emb.__file__).parent), str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-500:]
    assert np.abs(np.load(out) - ref_vectors).max() <= emb.REPRO_ATOL


# ------------------------------------------------------------------------------------------ unicode
def test_unicode_inputs_are_processed(st):
    inputs = emb.ACCENTED + emb.NFD_INPUTS + ["ÑANDÚ", "Ünïcödé 中文 🙂"]
    vectors = emb.encode_st(st, inputs)
    h = emb.health(vectors)
    assert h["all_finite"] and h["null_vectors"] == 0
    assert np.abs(h["norm_min"] - 1) <= emb.NORM_ATOL and np.abs(h["norm_max"] - 1) <= emb.NORM_ATOL
    unk = st.tokenizer.unk_token_id
    for text in emb.ACCENTED + emb.NFD_INPUTS:
        assert unk not in st.tokenizer(text)["input_ids"], f"unknown token in {text!r}"


def test_decomposed_input_is_not_corrupted(st):
    """After the project's own normalization (NFC) both spellings are the same string, hence the same vector."""
    assert [unicodedata.normalize("NFC", t) for t in emb.NFD_INPUTS] == emb.ACCENTED
    a = emb.encode_st(st, [unicodedata.normalize("NFC", t) for t in emb.NFD_INPUTS])
    b = emb.encode_st(st, emb.ACCENTED)
    assert np.abs(a - b).max() <= emb.REPRO_ATOL
