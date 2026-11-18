"""Phase 2a proof of concept: technical checks of the Granite embedding stack (experiments A to D).

Run from the repository root (the model must already be in the local Hugging Face cache):
    .venv\\Scripts\\python.exe experiments\\embedding_poc\\run_poc.py

Writes experiments/results/embedding_poc_2a/{manifest.json, summary.md} (versionable by the .gitignore rules)
and the raw embeddings as .npy files (ignored by Git). Nothing here compares different words with each other
or draws semantic conclusions.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import embedding as emb  # noqa: E402
import numpy as np  # noqa: E402

OUT_DIR = Path("experiments/results/embedding_poc_2a")
BATCH_SIZES = [1, 8, 32, 64]
REPEATS = 5
N_PERF_TEXTS = 64


def timed(fn):
    start = time.perf_counter()
    value = fn()
    return value, (time.perf_counter() - start) * 1000.0  # milliseconds


def stats(samples: list[float]) -> dict:
    return {"n": len(samples), "median_ms": round(statistics.median(samples), 2), "min_ms": round(min(samples), 2),
            "max_ms": round(max(samples), 2)}


def child_mode(path: str) -> int:
    np.save(path, emb.encode_st(emb.get_st(), emb.TECH_INPUTS))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-dump", help="internal: dump reference embeddings to this .npy and exit")
    args = parser.parse_args()
    if args.child_dump:
        return child_mode(args.child_dump)
    sys.stdout.reconfigure(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    result: dict = {}

    # ------------------------------------------------------------------ documentation of the real config
    config = emb.describe_config()

    # ------------------------------------------------------------------------------ Experiment A: load
    mem_before = emb.process_memory_mb()
    model, load_ms = timed(emb.get_st)
    mem_after_load = emb.process_memory_mb()
    summary = emb.pipeline_summary(model)
    first, first_ms = timed(lambda: emb.encode_st(model, ["casa"]))  # first inference: includes warm-up
    second, second_ms = timed(lambda: emb.encode_st(model, ["casa"]))
    ref = emb.encode_st(model, emb.TECH_INPUTS)
    np.save(OUT_DIR / "reference_st.npy", ref)
    a_health = emb.health(ref)
    a_pass = (summary["parameter_dtype"] == "torch.float32" and summary["device"] == "cpu" and summary["embedding_dimension"] == emb.EXPECTED_DIM
              and a_health["shape"][1] == emb.EXPECTED_DIM and a_health["all_finite"] and a_health["null_vectors"] == 0)
    result["A_load"] = {"pass": a_pass, "load_ms": round(load_ms, 1), "memory_before_mib": mem_before, "memory_after_load_mib": mem_after_load,
                        "pipeline": summary, "output_health": a_health, "revision_in_cache_path": config["snapshot_revision_from_path"]}

    # ------------------------------------------------------------ Experiment B: pooling and normalization
    stages = emb.st_stages(model, emb.TECH_INPUTS)
    explicit, explicit_load_ms = timed(emb.get_explicit)
    manual = explicit.encode(emb.TECH_INPUTS)
    np.save(OUT_DIR / "explicit_cls_l2.npy", manual)
    final_cmp = emb.compare(ref, manual)
    raw_manual = explicit.raw_cls(emb.TECH_INPUTS)
    raw_rel = np.linalg.norm(stages["raw_cls"].astype(np.float64) - raw_manual.astype(np.float64), axis=1) / np.linalg.norm(stages["raw_cls"].astype(np.float64), axis=1)
    ids_equal = stages["input_ids"] == explicit.token_ids(emb.TECH_INPUTS)
    raw_norms = np.linalg.norm(stages["raw_cls"], axis=1)
    once = np.abs(stages["raw_cls"] / np.linalg.norm(stages["raw_cls"], axis=1, keepdims=True) - stages["normalized"]).max()
    # control: a mean-pooled vector must be rejected by the same comparison (sensitivity of the check)
    import torch
    enc = explicit.tokenizer(emb.TECH_INPUTS, padding=True, return_tensors="pt")
    with torch.inference_mode():
        hidden = explicit.model(**enc)[0]
        mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
        mean_vec = torch.nn.functional.normalize((hidden * mask).sum(1) / mask.sum(1), dim=1).numpy()
    control = emb.compare(ref, mean_vec)
    b_pass = (final_cmp["min_cosine"] >= emb.COSINE_MIN and final_cmp["max_abs_diff"] <= emb.IMPL_ATOL and ids_equal
              and float(raw_rel.max()) <= emb.IMPL_ATOL and final_cmp["max_norm_deviation_a"] <= emb.NORM_ATOL
              and final_cmp["max_norm_deviation_b"] <= emb.NORM_ATOL and control["min_cosine"] < emb.COSINE_MIN
              and summary["pooling_mode"] == "cls" and summary["has_normalize_module"] and float(raw_norms.min()) > 2.0)
    per_input = [{"input": t, "cosine": float(c), "max_abs_diff": float(d)} for t, c, d in
                 zip(emb.TECH_INPUTS, emb.row_cosine(ref, manual), np.abs(ref.astype(np.float64) - manual.astype(np.float64)).max(axis=1))]
    result["B_pooling_normalization"] = {
        "pass": b_pass, "tolerances": {"cosine_min": emb.COSINE_MIN, "max_abs_diff": emb.IMPL_ATOL, "norm_deviation": emb.NORM_ATOL, "relative_raw_cls": emb.IMPL_ATOL},
        "config_declares": {"pooling_config": config["pooling_config"], "modules_json": config["modules_json"]},
        "st_modules_built": summary["modules"], "st_pooling_mode": summary["pooling_mode"],
        "token_embeddings_shape_st": list(stages["token_embeddings_shape"]), "token_ids_identical": ids_equal,
        "raw_cls_norm_min": float(raw_norms.min()), "raw_cls_norm_max": float(raw_norms.max()),
        "pooled_vector_divided_by_its_norm_vs_final_max_abs_diff": float(once),
        "raw_cls_relative_error_max": float(raw_rel.max()),
        "final_vectors": final_cmp, "mean_pooling_control": {"min_cosine": control["min_cosine"], "max_abs_diff": control["max_abs_diff"]},
        "attention_implementation": {"sentence_transformers": summary["attention_implementation"], "explicit": explicit.attention_implementation},
        "explicit_model_load_ms": round(explicit_load_ms, 1), "per_input": per_input,
        "limitation": "A second L2 normalization is idempotent on unit vectors, so duplicated normalization cannot be seen in the final vectors; "
                      "it is excluded by the module list (one Normalize), by the encode() defaults (normalize_embeddings=False) and by the raw CLS norms (not 1) in the stages.",
    }

    # ------------------------------------------------------------------------------ Experiment C
    again = emb.encode_st(model, emb.TECH_INPUTS)
    single = np.vstack([emb.encode_st(model, [t]) for t in emb.TECH_INPUTS])
    batches = {str(b): float(np.abs(emb.encode_st(model, emb.TECH_INPUTS, batch_size=b) - ref).max()) for b in (1, 2, 5, 64)}
    rev = emb.encode_st(model, emb.TECH_INPUTS[::-1])[::-1]
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "child.npy")
        proc = subprocess.run([sys.executable, __file__, "--child-dump", dump], capture_output=True, text=True, encoding="utf-8", errors="replace")
        child = np.load(dump) if proc.returncode == 0 else None
    nfd_vec = emb.encode_st(model, emb.NFD_INPUTS)
    nfc_vec = emb.encode_st(model, emb.ACCENTED)
    nfd_ids = [model.tokenizer(t)["input_ids"] for t in emb.NFD_INPUTS]
    nfc_ids = [model.tokenizer(t)["input_ids"] for t in emb.ACCENTED]
    unk = model.tokenizer.unk_token_id
    odd = emb.health(emb.encode_st(model, ["ÑANDÚ", "Ünïcödé 中文 🙂"]))
    swapped = ref.copy()
    swapped[[0, 1]] = swapped[[1, 0]]
    c_diffs = {"same_session_repeat": float(np.abs(again - ref).max()), "one_text_per_call": float(np.abs(single - ref).max()),
               "reversed_order": float(np.abs(rev - ref).max()), "fresh_process": float(np.abs(child - ref).max()) if child is not None else None,
               "batch_size_variants": batches}
    scalar_diffs = [v for k, v in c_diffs.items() if k != "batch_size_variants"] + list(batches.values())
    c_pass = (all(v is not None and v <= emb.REPRO_ATOL for v in scalar_diffs)
              and float(np.abs(swapped - ref).max()) > emb.IMPL_ATOL
              and all(unk not in ids for ids in nfd_ids + nfc_ids) and emb.health(nfd_vec)["all_finite"] and odd["all_finite"] and odd["null_vectors"] == 0)
    result["C_reproducibility"] = {
        "pass": c_pass, "tolerance": emb.REPRO_ATOL, "inputs": emb.TECH_INPUTS, "max_abs_diff": c_diffs, "child_returncode": proc.returncode,
        "order_sensitivity_check_max_abs_diff_when_two_rows_swapped": float(np.abs(swapped - ref).max()),
        "unicode": {"nfd_inputs_health": emb.health(nfd_vec), "no_unknown_token_in_nfc_or_nfd": all(unk not in ids for ids in nfd_ids + nfc_ids),
                    "nfd_token_ids_equal_nfc_token_ids": nfd_ids == nfc_ids, "nfd_vs_nfc_max_abs_diff": float(np.abs(nfd_vec - nfc_vec).max()),
                    "nfc_of_nfd_equals_original": [unicodedata.normalize("NFC", t) for t in emb.NFD_INPUTS] == emb.ACCENTED,
                    "mixed_script_and_emoji_health": odd},
    }

    # ------------------------------------------------------------------------------ Experiment D
    texts = [emb.TECH_INPUTS[i % len(emb.TECH_INPUTS)] for i in range(N_PERF_TEXTS)]
    warm_single = [timed(lambda: emb.encode_st(model, ["casa"]))[1] for _ in range(10)]
    single_loop = [timed(lambda: [emb.encode_st(model, [t]) for t in texts])[1] for _ in range(REPEATS)]
    batch_rows = {}
    for b in BATCH_SIZES:
        samples = [timed(lambda: emb.encode_st(model, texts, batch_size=b))[1] for _ in range(REPEATS)]
        s = stats(samples)
        s["per_text_ms_median"] = round(s["median_ms"] / N_PERF_TEXTS, 2)
        batch_rows[str(b)] = s
    ten = emb.TECH_INPUTS[:10]
    ten_samples = [timed(lambda: emb.encode_st(model, ten, batch_size=32))[1] for _ in range(REPEATS)]
    sl = stats(single_loop)
    sl["per_text_ms_median"] = round(sl["median_ms"] / N_PERF_TEXTS, 2)
    result["D_performance"] = {
        "note": "descriptive measurements, no thresholds; CPU only; torch.inference_mode; fp32",
        "first_inference_ms_one_text_including_warmup": round(first_ms, 2), "second_inference_ms_same_text": round(second_ms, 2),
        "later_single_text_calls": stats(warm_single), "n_texts_per_run": N_PERF_TEXTS, "repeats": REPEATS,
        "one_text_per_call_loop": sl, "batched_by_batch_size": batch_rows, "ten_texts_one_request_batch_size_32": stats(ten_samples),
        "model_load_ms": round(load_ms, 1), "memory_final_mib": emb.process_memory_mb(),
    }

    # --------------------------------------------------------------------------------------- manifest
    sections = ["A_load", "B_pooling_normalization", "C_reproducibility"]
    overall = all(result[s]["pass"] for s in sections)
    manifest = {
        "phase": "2a (embedding PoC)", "timestamp_utc": started.isoformat(), "model_id": emb.MODEL_ID, "model_revision": emb.REVISION,
        "device": "cpu", "libraries": emb.library_versions(), "machine": emb.machine_info(), "git": emb.git_state(),
        "tolerances_fixed_before_first_run": {"cosine_min": emb.COSINE_MIN, "repro_atol": emb.REPRO_ATOL, "impl_atol": emb.IMPL_ATOL, "norm_atol": emb.NORM_ATOL,
                                            "null_norm": emb.NULL_NORM, "source": "cosine_min and repro_atol: docs/acceptance-criteria-2c.md section 3; impl_atol, norm_atol: embedding.py (justified there)"},
        "model_config_declared_by_snapshot": config, "inputs": {"tech_inputs": emb.TECH_INPUTS, "nfd_inputs": emb.NFD_INPUTS},
        "results": result, "overall_pass": overall,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_summary(manifest), encoding="utf-8")
    for s in sections:
        print(f"[{'PASS' if result[s]['pass'] else 'FAIL'}] {s}")
    print(f"overall: {'PASS' if overall else 'FAIL'}   outputs: {OUT_DIR}")
    return 0 if overall else 1


def render_summary(m: dict) -> str:
    r, lib, mach, cfg = m["results"], m["libraries"], m["machine"], m["model_config_declared_by_snapshot"]
    a, b, c, d = r["A_load"], r["B_pooling_normalization"], r["C_reproducibility"], r["D_performance"]
    f = b["final_vectors"]
    ok = lambda x: "PASS" if x else "FAIL"  # noqa: E731
    lines = [
        "# Embedding PoC, Phase 2a: technical summary", "",
        f"Generated {m['timestamp_utc']} by `experiments/embedding_poc/run_poc.py`. Technical checks only (evidence level E0); no semantic conclusion is drawn from any input.", "",
        f"**Overall: {ok(m['overall_pass'])}** (A {ok(a['pass'])}, B {ok(b['pass'])}, C {ok(c['pass'])}; D is descriptive).", "",
        "**Relation to the earlier Phase 2a work.** This run extends `experiments/check_2a_correctness.py` and its results in `experiments/results/2a_20261103_004339/`, which already checked Sentence Transformers against the reference implementation and reproducibility (all passed) and are not replaced. Their two criteria are reused unchanged; this run adds staged pooling/normalization checks, Unicode, batch and order checks, performance, memory and a pytest suite.", "",
        "## Environment", "",
        f"- Python {lib['python']}, torch {lib['torch']} (CUDA build: {lib['torch_cuda']}; CUDA available: {lib['cuda_available']}), transformers {lib['transformers']}, "
        f"sentence-transformers {lib['sentence_transformers']}, numpy {lib['numpy']}, huggingface_hub {lib['huggingface_hub']}, tokenizers {lib['tokenizers']}, pytest {lib['pytest']}.",
        f"- {mach.get('cpu_name')}, {mach.get('physical_cores')} cores / {mach.get('logical_processors')} logical, {mach.get('ram_gib')} GiB RAM, {mach['os']}; torch threads {mach['torch_threads']}.",
        f"- Model `{m['model_id']}` at revision `{m['model_revision']}` (`model.safetensors` SHA-256 `{cfg['model_safetensors_sha256']}`), fp32 on CPU. Git commit {m['git']['commit'][:7]}.", "",
        "## Architecture and pooling (read from the snapshot, then confirmed on the loaded model)", "",
        f"- Architecture `{', '.join(cfg['architecture'])}`, {cfg['num_hidden_layers']} layers, {cfg['num_attention_heads']} heads, hidden size {cfg['hidden_size']}, vocabulary {cfg['vocab_size']}, weights stored as {cfg['stored_dtype']}, maximum sequence length {cfg['max_seq_length']}.",
        f"- `modules.json` declares {' -> '.join(cfg['modules_json'])}; `1_Pooling/config.json` sets `pooling_mode_cls_token = {cfg['pooling_config']['pooling_mode_cls_token']}` and every other mode false.",
        f"- Sentence Transformers built {' -> '.join(a['pipeline']['modules'])}; pooling mode `{a['pipeline']['pooling_mode']}`; effective attention `{a['pipeline']['attention_implementation']}`.",
        f"- Pooled CLS vectors have norms {b['raw_cls_norm_min']:.2f} to {b['raw_cls_norm_max']:.2f} (not unit); the Normalize module brings them to norm 1. So the three stages are separate: transformer output, CLS pooling, one L2 normalization.", "",
        "## Tolerances (fixed before the first run)", "",
        f"| Quantity | Tolerance | Source |", "|---|---|---|",
        f"| Cosine between paths | at least {m['tolerances_fixed_before_first_run']['cosine_min']} | acceptance-criteria-2c.md section 3 |",
        f"| Repeat, batch, order, fresh process | at most {m['tolerances_fixed_before_first_run']['repro_atol']} absolute | acceptance-criteria-2c.md section 3 |",
        f"| Max absolute difference, two paths | at most {m['tolerances_fixed_before_first_run']['impl_atol']} | `embedding.py` |",
        f"| Norm deviation from 1 | at most {m['tolerances_fixed_before_first_run']['norm_atol']} | `embedding.py` |", "",
        f"## A. Load ({ok(a['pass'])})", "",
        f"- Load time {a['load_ms'] / 1000:.1f} s (weights already in the local cache); working set {a['memory_before_mib'].get('working_set_mib')} MiB before, {a['memory_after_load_mib'].get('working_set_mib')} MiB after load.",
        f"- Output shape {a['output_health']['shape']}, finite: {a['output_health']['all_finite']}, null vectors: {a['output_health']['null_vectors']}, norms {a['output_health']['norm_min']:.7f} to {a['output_health']['norm_max']:.7f}.", "",
        f"## B. Pooling and normalization ({ok(b['pass'])})", "",
        f"- Token ids identical in both paths: {b['token_ids_identical']}.",
        f"- Final vectors: min cosine {f['min_cosine']:.9f}, max absolute difference {f['max_abs_diff']:.3e}, mean absolute difference {f['mean_abs_diff']:.3e}; norm deviation {f['max_norm_deviation_a']:.2e} (Sentence Transformers) and {f['max_norm_deviation_b']:.2e} (explicit).",
        f"- Pooled CLS vector before normalization, largest relative error {b['raw_cls_relative_error_max']:.3e}. Pooled vector divided by its own norm vs final vector: {b['pooled_vector_divided_by_its_norm_vs_final_max_abs_diff']:.3e}.",
        f"- Sensitivity control: a mean-pooled vector gives a minimum cosine of {b['mean_pooling_control']['min_cosine']:.4f} against the reference, so a wrong pooling would be rejected by the same check.",
        f"- Attention: {b['attention_implementation']['sentence_transformers']} (Sentence Transformers) and {b['attention_implementation']['explicit']} (explicit).",
        f"- Limitation: {b['limitation']}", "",
        f"## C. Reproducibility ({ok(c['pass'])})", "",
        "| Comparison | Max absolute difference |", "|---|---|",
    ]
    for k, v in c["max_abs_diff"].items():
        if k == "batch_size_variants":
            for bs, val in v.items():
                lines.append(f"| batch size {bs} vs reference | {val:.3e} |")
        else:
            lines.append(f"| {k.replace('_', ' ')} | {v:.3e} |")
    u = c["unicode"]
    lines += ["", f"- Order sensitivity: swapping two rows changes the matrix by {c['order_sensitivity_check_max_abs_diff_when_two_rows_swapped']:.3e}, far above the tolerance, so an order error would be detected.",
              f"- Unicode: no unknown token in NFC or NFD forms: {u['no_unknown_token_in_nfc_or_nfd']}; NFD and NFC token ids equal: {u['nfd_token_ids_equal_nfc_token_ids']}; NFD vs NFC vectors differ by at most {u['nfd_vs_nfc_max_abs_diff']:.3e}; "
              f"upper-case, mixed-script and emoji inputs finite: {u['mixed_script_and_emoji_health']['all_finite']}.", "",
              "## D. Performance (descriptive; no thresholds)", "",
              f"- First inference (one text, includes warm-up): {d['first_inference_ms_one_text_including_warmup']} ms; second: {d['second_inference_ms_same_text']} ms; later single-text calls: median {d['later_single_text_calls']['median_ms']} ms (min {d['later_single_text_calls']['min_ms']}, max {d['later_single_text_calls']['max_ms']}).",
              f"- {d['n_texts_per_run']} texts, {d['repeats']} repetitions each, median per run:", "", "| Mode | Run ms | ms per text |", "|---|---|---|",
              f"| one text per call | {d['one_text_per_call_loop']['median_ms']} | {d['one_text_per_call_loop']['per_text_ms_median']} |"]
    for bs, row in d["batched_by_batch_size"].items():
        lines.append(f"| batch size {bs} | {row['median_ms']} | {row['per_text_ms_median']} |")
    lines += ["", f"- Ten texts in one request (batch size 32): median {d['ten_texts_one_request_batch_size_32']['median_ms']} ms.",
              f"- Memory at the end of the run (two model copies loaded: Sentence Transformers and explicit): working set {d['memory_final_mib'].get('working_set_mib')} MiB, peak {d['memory_final_mib'].get('peak_working_set_mib')} MiB, private {d['memory_final_mib'].get('private_mib')} MiB.", "",
              "## Limits", "",
              "- Only fp32 was tested: the weights are stored as bfloat16 and run here as an exact upcast; bf16 inference was not tested.",
              "- Reproducibility was checked in the current environment (one machine, the installed versions, one fresh process). Other machines, other library versions and a clean installation were not tested.",
              "- Timings are descriptive measurements from one session with other processes running; they are not a benchmark.",
              "- Installing `requirements-poc.txt` into an empty virtual environment has not been tested.",
              "- The input set is tiny and fixed. Passing says the extraction is technically correct and reproducible; it does not show semantic quality.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
