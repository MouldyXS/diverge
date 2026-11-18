"""Embedding extraction for the Granite proof of concept (Phase 2a, technical checks only).

Two independent extraction paths are kept apart on purpose:

* reference path: Sentence Transformers (Transformer -> Pooling(CLS) -> Normalize, as the model ships it);
* explicit path: tokenizer + XLMRobertaModel from Transformers, first-token output of the last hidden
  state, then one L2 normalization (the recipe of the model card).

The configuration of the model, not an assumption, decides which pooling is applied: `describe_config`
reads modules.json / 1_Pooling/config.json from the pinned snapshot, and `pipeline_summary` reads the
modules that Sentence Transformers actually built.

Nothing here computes similarities between different words, and nothing here is part of the future application.
"""

from __future__ import annotations

import ctypes
import functools
import hashlib
import json
import os
import platform
import subprocess
import unicodedata
from ctypes import wintypes
from pathlib import Path

# The weights are already in the local Hugging Face cache (outside the repository). Network access is
# opt-in: set DIVERGE_POC_ALLOW_DOWNLOAD=1 to fetch the pinned revision. Must be decided before importing
# huggingface_hub / transformers.
if os.environ.get("DIVERGE_POC_ALLOW_DOWNLOAD") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402

MODEL_ID = "ibm-granite/granite-embedding-278m-multilingual"
REVISION = "a9cb5338491faf32b73dd17b714a31821c021bbf"
EXPECTED_DIM = 768

# ---------------------------------------------------------------------------------------------------
# Tolerances, fixed BEFORE the first run of this PoC (experiments/embedding_poc/README.md repeats them).
#
# COSINE_MIN and REPRO_ATOL come from docs/acceptance-criteria-2c.md section 3 and are reused unchanged.
# IMPL_ATOL and NORM_ATOL are new and justified here:
#   * Both paths run the same fp32 network on CPU. The only legitimate source of difference is padding
#     length and operation order (batch of different composition). fp32 machine epsilon is 1.2e-7, vector
#     components are of order 0.04 (unit norm, 768 dims), and 12 layers accumulate rounding, so a
#     difference of a few 1e-7 is expected. 1e-5 is ~100 times that, and still ~3 orders of magnitude
#     below the smallest meaningful structure of a unit vector (components of 1e-2). A real defect (a
#     wrong pooling, a missing or double normalization) produces differences of 1e-1 or more.
#   * NORM_ATOL: |‖v‖ - 1| for fp32 unit vectors is a few 1e-7 by construction; 1e-5 leaves margin.
#   * A vector counts as "null" when its norm is below NULL_NORM (a unit vector has norm 1).
# ---------------------------------------------------------------------------------------------------
COSINE_MIN = 0.99999
REPRO_ATOL = 1e-6
IMPL_ATOL = 1e-5
NORM_ATOL = 1e-5
NULL_NORM = 0.5

COMMON = ["casa", "perro", "árbol"]
ACCENTED = ["canción", "año", "ñandú"]
REGIONAL = ["guagua", "chuchaqui", "canguil"]
PHRASES = ["casa de campo", "perro caliente", "hasta luego"]
TECH_INPUTS = COMMON + ACCENTED + REGIONAL + PHRASES
# Same strings in decomposed form (NFD): a technical check of Unicode handling only.
NFD_INPUTS = [unicodedata.normalize("NFD", t) for t in ACCENTED]


# ------------------------------------------------------------------------------------------ environment
def process_memory_mb() -> dict:
    """Working set / peak working set / private bytes of this process, in MiB (Windows only)."""

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]

    if os.name != "nt":
        return {"available": False}
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return {"available": False}
    mib = 1024 * 1024
    return {"available": True, "working_set_mib": round(counters.WorkingSetSize / mib, 1),
            "peak_working_set_mib": round(counters.PeakWorkingSetSize / mib, 1),
            "private_mib": round(counters.PrivateUsage / mib, 1)}


def machine_info() -> dict:
    info = {"os": platform.platform(), "python": platform.python_version(), "machine": platform.machine(),
            "logical_cpus": os.cpu_count(), "torch_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads()}
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "$c=Get-CimInstance Win32_Processor|Select-Object -First 1;"
                              "$m=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;"
                              "\"$($c.Name.Trim())|$($c.NumberOfCores)|$($c.NumberOfLogicalProcessors)|$m\""],
                             capture_output=True, text=True, timeout=30).stdout.strip().split("|")
        info.update({"cpu_name": out[0], "physical_cores": int(out[1]), "logical_processors": int(out[2]),
                     "ram_gib": round(int(out[3]) / 1024**3, 1)})
    except Exception:  # noqa: BLE001 - informational only
        info["cpu_name"] = platform.processor()
    return info


def library_versions() -> dict:
    import huggingface_hub
    import sentence_transformers
    import tokenizers
    import transformers

    versions = {"python": platform.python_version(), "torch": torch.__version__, "torch_cuda": torch.version.cuda,
                "cuda_available": torch.cuda.is_available(), "transformers": transformers.__version__,
                "sentence_transformers": sentence_transformers.__version__, "numpy": np.__version__,
                "huggingface_hub": huggingface_hub.__version__, "tokenizers": tokenizers.__version__}
    try:
        import pytest

        versions["pytest"] = pytest.__version__
    except ImportError:
        versions["pytest"] = None
    return versions


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
        except Exception:  # noqa: BLE001
            return "unavailable"

    return {"commit": run("rev-parse", "HEAD"), "dirty": run("status", "--porcelain", "--untracked-files=no") != ""}


# ---------------------------------------------------------------------------------------- documentation
def snapshot_dir() -> Path:
    """Directory of the pinned snapshot inside the local Hugging Face cache (never inside the repository)."""
    from huggingface_hub import try_to_load_from_cache

    cached = try_to_load_from_cache(MODEL_ID, "config.json", revision=REVISION)
    if not isinstance(cached, str):
        raise RuntimeError(f"{MODEL_ID}@{REVISION} is not in the local cache; set DIVERGE_POC_ALLOW_DOWNLOAD=1 once")
    return Path(cached).parent


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def describe_config() -> dict:
    """What the pinned snapshot itself declares: architecture, pooling mode, module list, file hashes."""
    d = snapshot_dir()
    read = lambda rel: json.loads((d / rel).read_text(encoding="utf-8"))  # noqa: E731
    cfg, pool, mods, st_cfg = read("config.json"), read("1_Pooling/config.json"), read("modules.json"), read("sentence_bert_config.json")
    return {
        "snapshot_revision_from_path": d.name,
        "architecture": cfg["architectures"], "model_type": cfg["model_type"], "hidden_size": cfg["hidden_size"],
        "num_hidden_layers": cfg["num_hidden_layers"], "num_attention_heads": cfg["num_attention_heads"],
        "vocab_size": cfg["vocab_size"], "stored_dtype": cfg.get("torch_dtype"),
        "pooling_config": pool, "modules_json": [m["type"].rsplit(".", 1)[-1] for m in mods],
        "modules_json_has_normalize": any(m["type"].endswith("Normalize") for m in mods),
        "max_seq_length": st_cfg["max_seq_length"],
        "files": sorted(p.name if p.parent == d else f"{p.parent.name}/{p.name}" for p in d.rglob("*") if p.is_file() or p.is_symlink()),
        "model_safetensors_sha256": _sha256(d / "model.safetensors"),
    }


# ------------------------------------------------------------------------------------- reference path
@functools.lru_cache(maxsize=1)
def get_st():
    """Sentence Transformers model, fp32, CPU, pinned revision. Loaded once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_ID, revision=REVISION, device="cpu", model_kwargs={"dtype": torch.float32})


def pipeline_summary(model) -> dict:
    """The modules Sentence Transformers really built (pooling mode read from the module, not assumed)."""
    modules = [type(m).__name__ for m in model]
    pooling = next(m for m in model if type(m).__name__ == "Pooling")
    return {"modules": modules, "pooling_mode": getattr(pooling, "pooling_mode", None),
            "embedding_dimension": model.get_embedding_dimension(), "max_seq_length": model.max_seq_length,
            "has_normalize_module": "Normalize" in modules, "attention_implementation": str(getattr(model[0].auto_model.config, "_attn_implementation", "unknown")),
            "parameter_dtype": str(next(model.parameters()).dtype), "device": str(next(model.parameters()).device)}


def encode_st(model, texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Reference embeddings. `normalize_embeddings` is left False: the model's own Normalize module already
    normalizes once, and asking again would apply the operation twice."""
    model.eval()
    with torch.inference_mode():
        return model.encode(list(texts), batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False)


def st_stages(model, texts: list[str]) -> dict:
    """Run the three Sentence Transformers modules one by one to separate transformer output, pooling and normalization."""
    model.eval()
    with torch.inference_mode():
        features = model.preprocess(list(texts))
        after_transformer = model[0](dict(features))
        after_pooling = model[1](dict(after_transformer))
        raw_cls = after_pooling["sentence_embedding"].clone()
        after_norm = model[2](dict(after_pooling))
    return {"input_ids": [ids[mask.bool()].tolist() for ids, mask in zip(features["input_ids"], features["attention_mask"])],
            "token_embeddings_shape": tuple(after_transformer["token_embeddings"].shape),
            "raw_cls": raw_cls.numpy(), "normalized": after_norm["sentence_embedding"].numpy()}


# --------------------------------------------------------------------------------------- explicit path
class ExplicitExtractor:
    """Tokenizer + XLMRobertaModel from Transformers; CLS (first token) pooling and one L2 normalization."""

    def __init__(self) -> None:
        from transformers import AutoModel, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
        self.model = AutoModel.from_pretrained(MODEL_ID, revision=REVISION, dtype=torch.float32)
        self.model.eval()
        self.max_length = 512

    def token_ids(self, texts: list[str]) -> list[list[int]]:
        enc = self.tokenizer(list(texts), padding=True, truncation=True, max_length=self.max_length, return_tensors="pt")
        return [ids[mask.bool()].tolist() for ids, mask in zip(enc["input_ids"], enc["attention_mask"])]

    def raw_cls(self, texts: list[str]) -> np.ndarray:
        with torch.inference_mode():
            enc = self.tokenizer(list(texts), padding=True, truncation=True, max_length=self.max_length, return_tensors="pt")
            hidden = self.model(**enc)[0]  # last hidden state, shape (batch, tokens, 768)
            return hidden[:, 0].numpy()  # pooling: first token (<s>), the CLS position

    def encode(self, texts: list[str]) -> np.ndarray:
        raw = torch.from_numpy(self.raw_cls(texts))
        return torch.nn.functional.normalize(raw, p=2, dim=1).numpy()  # the single normalization

    @property
    def attention_implementation(self) -> str:
        return str(getattr(self.model.config, "_attn_implementation", "unknown"))


@functools.lru_cache(maxsize=1)
def get_explicit() -> ExplicitExtractor:
    return ExplicitExtractor()


# ------------------------------------------------------------------------------------------ comparisons
def row_cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    return np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    """Numerical comparison of two embedding matrices computed from the same inputs, in the same order."""
    diff = np.abs(a.astype(np.float64) - b.astype(np.float64))
    cos = row_cosine(a, b)
    return {"shape_a": list(a.shape), "shape_b": list(b.shape), "max_abs_diff": float(diff.max()),
            "mean_abs_diff": float(diff.mean()), "min_cosine": float(cos.min()), "worst_row": int(np.argmin(cos)),
            "max_norm_deviation_a": float(np.abs(np.linalg.norm(a.astype(np.float64), axis=1) - 1).max()),
            "max_norm_deviation_b": float(np.abs(np.linalg.norm(b.astype(np.float64), axis=1) - 1).max())}


def health(vectors: np.ndarray) -> dict:
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    return {"shape": list(vectors.shape), "all_finite": bool(np.isfinite(vectors).all()), "dtype": str(vectors.dtype),
            "norm_min": float(norms.min()), "norm_max": float(norms.max()), "null_vectors": int((norms < NULL_NORM).sum())}
