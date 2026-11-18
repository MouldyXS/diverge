"""Phase 2a: technical correctness checks for the embedding stack (evidence level E0).

Criteria are fixed in docs/acceptance-criteria-2c.md, section 3:

1. Sentence Transformers vectors match the reference implementation
   (first token + L2 normalization, plain Transformers): cosine >= 0.99999.
2. The effective attention implementation is recorded and is not Flash Attention 2.
3. Reproducibility within 1e-6: same session, different batch composition and
   order, and a fresh process.
4. The installed torch is a CPU build (torch.version.cuda is None).

The script never touches the network (HF_HUB_OFFLINE=1): the model must already be
in the local Hugging Face cache at the pinned revision.

Usage (from the repository root):
    .venv\\Scripts\\python.exe experiments\\check_2a_correctness.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"

import numpy as np  # noqa: E402
import torch  # noqa: E402

MODEL_ID = "ibm-granite/granite-embedding-278m-multilingual"
REVISION = "a9cb5338491faf32b73dd17b714a31821c021bbf"

COSINE_MIN = 0.99999
REPRO_TOL = 1e-6

# Mixed test words: accents, ñ, ü, regionalisms, diacritic-only pairs, nonsense, a proper noun, a verb.
RAW_WORDS = [
    "casa", "perro", "mesa", "árbol", "niño", "año", "ano", "camión", "pingüino",
    "corazón", "guagua", "chompa", "chulla", "palta", "computadora", "sí", "si",
    "él", "el", "papá", "papa", "xqzvbn", "asdfgh", "tarvelo", "bicicleta",
    "montaña", "cuchara", "música", "libertad", "Quito", "correr",
]


def normalize(word: str) -> str:
    """strip -> NFC -> casefold -> NFC (the normalization rule documented in docs/scoring.md section 1)."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", word.strip()).casefold())


WORDS = [normalize(w) for w in RAW_WORDS]


def load_sentence_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL_ID,
        revision=REVISION,
        device="cpu",
        model_kwargs={"dtype": torch.float32},
    )


def embed_st(model, words: list[str]) -> np.ndarray:
    with torch.inference_mode():
        return model.encode(words, convert_to_numpy=True, show_progress_bar=False)


def embed_reference(words: list[str]) -> tuple[np.ndarray, str]:
    """Reference path from the model card: first-token output + L2 normalization."""
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
    model = AutoModel.from_pretrained(MODEL_ID, revision=REVISION, dtype=torch.float32)
    model.eval()
    attn = str(getattr(model.config, "_attn_implementation", "unknown"))
    with torch.inference_mode():
        batch = tokenizer(words, padding=True, truncation=True, max_length=512, return_tensors="pt")
        out = model(**batch)
        vec = torch.nn.functional.normalize(out[0][:, 0], dim=1)
    return vec.numpy(), attn


def row_cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    b = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.sum(a * b, axis=1)


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
        except Exception:  # noqa: BLE001 - informational only
            return "unavailable"

    return {"commit": run("rev-parse", "HEAD"), "dirty": run("status", "--porcelain") != ""}


def library_versions() -> dict:
    import sentence_transformers
    import transformers
    import huggingface_hub

    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "sentence_transformers": sentence_transformers.__version__,
        "transformers": transformers.__version__,
        "huggingface_hub": huggingface_hub.__version__,
        "numpy": np.__version__,
        "torch_threads": torch.get_num_threads(),
    }


def child_mode(out_path: str) -> int:
    """Fresh-process run: embed WORDS and dump them for the parent to compare."""
    model = load_sentence_model()
    np.save(out_path, embed_st(model, WORDS))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-dump", help="internal: dump embeddings to this .npy file and exit")
    args = parser.parse_args()
    if args.child_dump:
        return child_mode(args.child_dump)

    sys.stdout.reconfigure(encoding="utf-8")
    results: dict[str, dict] = {}

    # --- Check 4: CPU build
    results["cpu_build"] = {"pass": torch.version.cuda is None and not torch.cuda.is_available(),
                            "torch_cuda": torch.version.cuda}

    st_model = load_sentence_model()
    st_vecs = embed_st(st_model, WORDS)

    # --- Check 1: ST vs reference
    ref_vecs, ref_attn = embed_reference(WORDS)
    cos = row_cosine(st_vecs, ref_vecs)
    norms = np.linalg.norm(st_vecs, axis=1)
    worst = int(np.argmin(cos))
    results["st_vs_reference"] = {
        "pass": bool(cos.min() >= COSINE_MIN),
        "min_cosine": float(cos.min()),
        "worst_word": WORDS[worst],
        "criterion": COSINE_MIN,
        "st_norm_min": float(norms.min()),
        "st_norm_max": float(norms.max()),
        "st_vectors_l2_normalized": bool(np.allclose(norms, 1.0, atol=1e-5)),
    }

    # --- Check 2: attention implementation
    st_attn = str(getattr(st_model[0].auto_model.config, "_attn_implementation", "unknown"))
    results["attention"] = {
        "pass": "flash" not in st_attn.lower() and "flash" not in ref_attn.lower(),
        "sentence_transformers": st_attn,
        "reference": ref_attn,
    }

    # --- Check 3: reproducibility
    again = embed_st(st_model, WORDS)
    reversed_vecs = embed_st(st_model, WORDS[::-1])[::-1]
    single = np.vstack([embed_st(st_model, [w]) for w in WORDS])
    half = len(WORDS) // 2
    split = np.vstack([embed_st(st_model, WORDS[:half]), embed_st(st_model, WORDS[half:])])
    with tempfile.TemporaryDirectory() as tmp:
        dump = os.path.join(tmp, "child.npy")
        proc = subprocess.run([sys.executable, __file__, "--child-dump", dump],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        child = np.load(dump) if proc.returncode == 0 else None
    diffs = {
        "same_session_repeat": float(np.abs(st_vecs - again).max()),
        "reversed_order": float(np.abs(st_vecs - reversed_vecs).max()),
        "one_word_per_call": float(np.abs(st_vecs - single).max()),
        "two_half_batches": float(np.abs(st_vecs - split).max()),
        "fresh_process": float(np.abs(st_vecs - child).max()) if child is not None else None,
    }
    results["reproducibility"] = {
        "pass": all(v is not None and v <= REPRO_TOL for v in diffs.values()),
        "max_abs_diff": diffs,
        "tolerance": REPRO_TOL,
        "child_returncode": proc.returncode,
    }

    overall = all(r["pass"] for r in results.values())

    manifest = {
        "phase": "2a",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "model_revision": REVISION,
        "device": "cpu",
        "model_dtype": str(next(st_model.parameters()).dtype),
        "words": WORDS,
        "libraries": library_versions(),
        "git": git_state(),
        "criteria_source": "docs/acceptance-criteria-2c.md section 3",
        "results": results,
        "overall_pass": overall,
    }

    out_dir = Path("experiments/results") / f"2a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"model dtype: {manifest['model_dtype']}   attention: {st_attn}")
    for name, res in results.items():
        print(f"[{'PASS' if res['pass'] else 'FAIL'}] {name}: "
              + json.dumps({k: v for k, v in res.items() if k != 'pass'}, ensure_ascii=False))
    print(f"overall: {'PASS' if overall else 'FAIL'}   manifest: {out_dir / 'manifest.json'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
