"""Regression against the DAT7 baseline v0.1, with the local reference model.

Markers: every test below except `test_missing_references_fail_instead_of_skipping` is marked `model`. The two that compare
against the private reference files, `test_baseline_reproduced` and `test_dat7_function_reproduces_the_indices`, are also
marked `baseline`. Tests marked `baseline` are deselected by default and run only when `--baseline` is given (see
`conftest.py`). A plain `pytest -m model` therefore does not show that the baseline was checked.

The baseline (`experiments/results/semantic_baseline_dat7_v0.1/`, private reference files that are not part of this
distribution) encoded each set with one `encode_st` call of its seven words in CSV order, batch size 32, CPU, fp32. These
tests use the same conditions through the engine, and read the reference files only after checking their SHA-256.

With `--baseline`, missing reference files make the `baseline` tests **fail**, never skip: a skipped regression would let a
run exit successfully without having checked the baseline. Only a successful run with `--baseline`, with the reference files
in place, means the baseline was compared.

Tolerances, fixed before the first run and not changed afterwards:
* embeddings: REPRO_ATOL = 1e-6 per component, imported from experiments/embedding_poc/embedding.py;
* index: strictly below INDEX_ATOL = 1e-6, the value the baseline runner used for its own checks;
* pair similarities and distances: PAIR_ATOL = INDEX_ATOL / 100 = 1e-8. No pair tolerance existed; this one is derived,
  not relaxed: the index is 100 x the mean of 21 distances, so pair errors within 1e-8 keep the index within 1e-6.
"""

import ast
import csv
import hashlib
import socket
from pathlib import Path

import numpy as np
import pytest

from app.engine import GraniteEmbedder, REFERENCE_MODEL, analyze_dat7, analyze_vectors, select_dat7

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / "experiments/results/semantic_baseline_dat7_v0.1"
SOURCE = REPO / "experiments/wordsets/curated/diverse_sets_v0.1.csv"
REFERENCE_SHA256 = {  # hashes of the preserved private baseline files
    "baseline_results.csv": "55db0def52b51cd7cbe84ba7578c110a968bf6244624bd3c8c22d5d0671c9967",
    "pairwise_distances.csv": "cf6cec877854441d36ff842345ae0b3d618346c348d443445dc4dc2746243681",
    "embeddings_dat7.npz": "5bc34f9dcaa1a79bf23d0b0c651a9729fa548b52808be22a4595e2259d24d2ac",
}
SOURCE_SHA256_LF = "6dbcf2d0f3736dfbfab51ba805f713040cdd19acaff916def2b60eaf8c2cf142"
WEIGHTS_SHA256 = "b522423ae15d1a6fd48c55ef4f599c0c2c0737603da94e4b4815760c2c06ebac"

REPRO_ATOL = 1e-6
INDEX_ATOL = 1e-6
PAIR_ATOL = INDEX_ATOL / 100


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def no_network():
    attempts = []
    original = socket.socket.connect

    def guarded(self, address):
        attempts.append(repr(address))
        raise OSError(f"network disabled in model tests: {address!r}")

    socket.socket.connect = guarded
    yield attempts
    socket.socket.connect = original


def load_reference(baseline_dir: Path = BASELINE, source: Path = SOURCE) -> dict:
    """Read the reference files after checking them. Fails, never skips, when any is missing or altered."""
    required = [baseline_dir / name for name in REFERENCE_SHA256] + [source]
    missing = [path for path in required if not path.is_file()]
    if missing:
        pytest.fail(
            "DAT7 baseline regression NOT run: reference files are missing.\n"
            + "".join(f"  missing: {path}\n" for path in missing)
            + f"Expected directory: {baseline_dir}\n"
            "These are private reference files and are not part of the public distribution, so a clone does not have them "
            "(see backend/README.md, 'Reference files'); do not regenerate them. "
            'The tests that do not need them run without --baseline: pytest -m "not model".',
            pytrace=False,
        )
    for name, digest in REFERENCE_SHA256.items():
        assert _sha(baseline_dir / name) == digest, f"{name} differs from the preserved baseline"
    assert hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == SOURCE_SHA256_LF
    with open(baseline_dir / "baseline_results.csv", encoding="utf-8", newline="") as handle:
        results = list(csv.DictReader(handle))
    with open(baseline_dir / "pairwise_distances.csv", encoding="utf-8", newline="") as handle:
        pairs = list(csv.DictReader(handle))
    with open(source, encoding="utf-8", newline="") as handle:
        sets = list(csv.DictReader(handle))
    stored = np.load(baseline_dir / "embeddings_dat7.npz", allow_pickle=False)
    return {"results": results, "pairs": pairs, "sets": sets, "embeddings": stored["embeddings"], "set_ids": list(stored["set_ids"])}


@pytest.fixture(scope="module")
def reference():
    return load_reference()


def test_missing_references_fail_instead_of_skipping():
    """No model needed: a directory without the reference files must fail with an actionable message."""
    absent = Path(__file__).resolve().parent / "no-such-reference-directory"
    assert not absent.exists()
    with pytest.raises(pytest.fail.Exception) as info:
        load_reference(absent)
    message = str(info.value)
    assert "NOT run" in message and "baseline_results.csv" in message and "backend/README.md" in message
    assert not absent.exists()  # nothing was created


@pytest.fixture(scope="module")
def embedder(no_network):
    return GraniteEmbedder()


@pytest.mark.model
def test_tolerances_match_the_existing_definitions():
    """Read REPRO_ATOL from embedding.py without importing it: importing would set HF_HUB_OFFLINE as a side effect."""
    tree = ast.parse((REPO / "experiments/embedding_poc/embedding.py").read_text(encoding="utf-8"))
    values = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "REPRO_ATOL"}
    assert REPRO_ATOL == values["REPRO_ATOL"]
    assert PAIR_ATOL == INDEX_ATOL / 100


@pytest.mark.model
def test_model_identity_and_configuration(embedder, no_network):
    info = embedder.describe()
    assert info["model_id"] == REFERENCE_MODEL.model_id
    assert info["snapshot_revision"] == REFERENCE_MODEL.revision
    assert info["modules"] == ["Transformer", "Pooling", "Normalize"]
    assert info["pooling_mode"] == "cls"
    assert info["embedding_dimension"] == 768
    assert info["batch_size"] == 32
    assert isinstance(info["can_flatten_inputs"], bool)
    assert info["hf_hub_offline"] is True
    assert embedder.weights_sha256() == WEIGHTS_SHA256
    assert no_network == []


@pytest.mark.model
@pytest.mark.baseline
def test_baseline_reproduced(embedder, reference, no_network):
    results = {r["set_id"]: r for r in reference["results"]}
    pairs_by_set: dict[str, list[dict]] = {}
    for row in reference["pairs"]:
        pairs_by_set.setdefault(row["set_id"], []).append(row)
    assert len(reference["sets"]) == 14 and len(reference["pairs"]) == 294
    worst = {"embedding": 0.0, "similarity": 0.0, "distance": 0.0, "index": 0.0}
    for row in reference["sets"]:
        set_id = row["set_id"]
        entries = [row[f"w{k}"] for k in range(1, 11)]
        selection = select_dat7(entries)
        assert "|".join(selection.words) == results[set_id]["words_used"], set_id

        vectors = embedder.encode(list(selection.words))  # one call, seven words, entry order, batch size 32
        stored = reference["embeddings"][reference["set_ids"].index(set_id)]
        worst["embedding"] = max(worst["embedding"], float(np.abs(vectors.astype(np.float64) - stored.astype(np.float64)).max()))

        analysis = analyze_vectors(selection.words, vectors)
        expected_pairs = sorted(pairs_by_set[set_id], key=lambda r: int(r["pair_number"]))
        assert len(analysis.pairs) == len(expected_pairs) == 21
        for score, expected in zip(analysis.pairs, expected_pairs):
            assert (score.word_i, score.word_j) == (expected["word_i"], expected["word_j"])
            assert (score.i + 1, score.j + 1) == (int(expected["position_i"]), int(expected["position_j"]))
            worst["similarity"] = max(worst["similarity"], abs(score.similarity - float(expected["cosine_similarity"])))
            worst["distance"] = max(worst["distance"], abs(score.distance - float(expected["cosine_distance"])))
        index = analysis.mean_distance * 100.0
        worst["index"] = max(worst["index"], abs(index - float(results[set_id]["semantic_divergence_index"])))

    print(f"\nbaseline regression, worst absolute differences: {worst}")
    assert worst["embedding"] <= REPRO_ATOL
    assert worst["similarity"] <= PAIR_ATOL
    assert worst["distance"] <= PAIR_ATOL
    assert worst["index"] < INDEX_ATOL
    assert no_network == []


@pytest.mark.model
@pytest.mark.baseline
def test_dat7_function_reproduces_the_indices(embedder, reference):
    results = {r["set_id"]: float(r["semantic_divergence_index"]) for r in reference["results"]}
    for row in reference["sets"]:
        result = analyze_dat7(embedder, [row[f"w{k}"] for k in range(1, 11)])
        assert result.index is not None
        assert abs(result.index - results[row["set_id"]]) < INDEX_ATOL, row["set_id"]
