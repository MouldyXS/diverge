"""Model configuration and embedding generation.

`Embedder` is the interface the analysis functions use, so tests can pass synthetic vectors without a model.
`GraniteEmbedder` wraps the reference model with the encoding conditions of the DAT7 baseline: one call per request,
in entry order, `batch_size = 32`, `normalize_embeddings` left False (the model's own `Normalize` module normalizes
once), CPU, fp32, under `torch.inference_mode()` (same as `encode_st` in `experiments/embedding_poc/embedding.py`).

Heavy libraries are imported only when a `GraniteEmbedder` is created; importing this module needs NumPy only.
The model is loaded from the local Hugging Face cache with `local_files_only=True`; nothing is downloaded.

`local_files_only` is not enough to stay offline: huggingface_hub 2.4.0 fetches an agent registry from the Hub when it
builds request headers (`huggingface_hub/utils/_detect_agent.py`), unless offline mode is on.

How offline mode works in the installed huggingface_hub 2.4.0: `constants.HF_HUB_OFFLINE` is computed **once, when
the module is imported**, from `HF_HUB_OFFLINE` or `TRANSFORMERS_OFFLINE` (`constants.py:194`). The public function
`huggingface_hub.constants.is_offline_mode()` returns it, and transformers asks that function (`utils/hub.py`). Changing
the environment variable after the import has no effect. So `GraniteEmbedder`:

1. sets `HF_HUB_OFFLINE=1` only if the variable is unset, as `experiments/embedding_poc/embedding.py` does;
2. imports `huggingface_hub.constants` and checks the *effective* state with `is_offline_mode()`, before importing torch
   or Sentence Transformers and before any model file is touched;
3. raises `EngineConfigError` if offline mode is not effectively active: for example, when the variable is set to a false
   value, or when huggingface_hub was imported earlier in the process without it. No library constant is modified.

Pending decisions (docs/decisions.md, D21 section 10) are not taken here: maximum words per request and the policy
above 32 words. With more than `batch_size` texts, Sentence Transformers splits the request into several batches;
`describe()` reports the batch size so callers can see it.
"""

from __future__ import annotations

import hashlib
import os
import platform
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from .errors import EngineConfigError, EngineInputError


@dataclass(frozen=True)
class ModelSpec:
    """What the engine expects of the model. Loading fails if the loaded model differs."""

    model_id: str
    revision: str
    device: str = "cpu"
    dtype: str = "float32"
    batch_size: int = 32
    expected_dimension: int = 768
    expected_pooling: str = "cls"
    expected_modules: tuple[str, ...] = ("Transformer", "Pooling", "Normalize")


REFERENCE_MODEL = ModelSpec(
    model_id="ibm-granite/granite-embedding-278m-multilingual",
    revision="a9cb5338491faf32b73dd17b714a31821c021bbf",
)


@runtime_checkable
class Embedder(Protocol):
    """Anything that turns a list of texts into one vector per text, in the same order.

    `max_input_tokens` is the inclusive limit of tokens per text, special tokens included, above which the encoder
    would not represent the whole text. `count_tokens` returns one count per text, in order, counted exactly as
    `encode` would tokenize the text but without truncation.
    """

    @property
    def max_input_tokens(self) -> int: ...

    def count_tokens(self, texts: Sequence[str]) -> list[int]: ...

    def encode(self, texts: Sequence[str]) -> np.ndarray: ...

    def describe(self) -> dict: ...


def ensure_offline() -> None:
    """Make Hugging Face offline mode effective, or fail before any model library is imported.

    Sets `HF_HUB_OFFLINE=1` only if it is unset, then checks the state that huggingface_hub actually uses. It does not
    import torch, transformers or Sentence Transformers, and makes no network request.
    """
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from huggingface_hub import constants as hub_constants

    if not hub_constants.is_offline_mode():
        raise EngineConfigError(
            "Hugging Face offline mode is not effectively active: huggingface_hub.constants.is_offline_mode() is False "
            f"(HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE')!r} in the environment now). The library reads the variable "
            "once, when it is first imported. Set HF_HUB_OFFLINE=1 before anything imports huggingface_hub, transformers "
            "or sentence_transformers, or create GraniteEmbedder before those imports. The model was not loaded."
        )


def _check_texts(texts: Sequence[str]) -> list[str]:
    items = list(texts)
    if not items:
        raise EngineInputError("at least one text is needed")
    if not all(isinstance(t, str) for t in items):
        raise EngineInputError("every text must be a string")
    return items


class GraniteEmbedder:
    """The reference model, loaded once per instance, offline."""

    def __init__(self, spec: ModelSpec = REFERENCE_MODEL) -> None:
        ensure_offline()
        if spec.device != "cpu" or spec.dtype != "float32":
            raise EngineConfigError("only CPU and fp32 are supported")
        import torch
        from sentence_transformers import SentenceTransformer

        self.spec = spec
        self._torch = torch
        self.model = SentenceTransformer(spec.model_id, revision=spec.revision, device=spec.device,
                                         model_kwargs={"dtype": torch.float32}, local_files_only=True)
        self.model.eval()
        self._check_loaded()
        self._check_tokenization()

    def _check_tokenization(self) -> None:
        """Make sure `count_tokens` counts exactly what `encode` feeds the model, or refuse to load.

        Sentence Transformers 6.2.0 tokenizes text in `Transformer.preprocess` by calling the module's processor (the
        tokenizer) with `padding=True, truncation="longest_first"` and its default special tokens, truncating at
        `tokenizer.model_max_length`, unless the module has its own `processing_kwargs` or a prompt is applied. The
        configuration checks below rule those out; the two probes then compare the count with the real preprocessing
        path (the public `SentenceTransformer.preprocess`; tokenization only, no inference). Equivalence with the
        installed version is also covered by the model tests.
        """
        transformer = self.model[0]
        tokenizer = self.model.tokenizer
        problems = []
        if tokenizer is None or not callable(tokenizer):
            problems.append("no callable tokenizer")
        elif getattr(transformer, "processor", tokenizer) is not tokenizer:
            problems.append("the text processor is not the tokenizer")
        if getattr(transformer, "processing_kwargs", None):
            problems.append("module processing_kwargs are set")
        if self.model.default_prompt_name is not None:
            problems.append("a default prompt is applied")
        if problems:
            raise EngineConfigError("token counting cannot match the encoding path: " + "; ".join(problems))
        limit = self.max_input_tokens
        if getattr(tokenizer, "model_max_length", None) != limit:
            raise EngineConfigError("the tokenizer limit differs from the model context limit")

        def preprocessed_length(text: str) -> int:
            return int(self.model.preprocess([text])["attention_mask"][0].sum())

        short, long = "casa", "ñ" * (limit + 8)
        short_count, long_count = self.count_tokens([short, long])
        if short_count != preprocessed_length(short):
            raise EngineConfigError("token counts differ from the encoding path")
        if long_count <= limit or preprocessed_length(long) != limit:
            raise EngineConfigError("the encoding path does not truncate at the reported context limit")

    @property
    def max_input_tokens(self) -> int:
        """Effective context of the loaded model, special tokens included (`SentenceTransformer.max_seq_length`)."""
        limit = self.model.max_seq_length
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise EngineConfigError(f"the loaded model reports no usable context limit: {limit!r}")
        return limit

    def count_tokens(self, texts: Sequence[str]) -> list[int]:
        """Token count of each text, in order, with the model's own tokenizer: special tokens included, no truncation,
        no padding, no prompt. One tokenizer call for all texts. The text is used as given, so pass the same normalized
        text that `encode` receives."""
        items = list(texts)
        if not all(isinstance(t, str) for t in items):
            raise EngineInputError("every text must be a string")
        if not items:
            return []
        try:
            encoded = self.model.tokenizer(items, add_special_tokens=True, truncation=False, padding=False, verbose=False)
            counts = [len(ids) for ids in encoded["input_ids"]]
        except Exception as exc:  # noqa: BLE001 - a tokenizer failure is a configuration error
            raise EngineConfigError(f"the tokenizer failed ({type(exc).__name__})") from exc
        if len(counts) != len(items):
            raise EngineConfigError("the tokenizer returned a different number of sequences")
        return counts

    def _check_loaded(self) -> None:
        modules = tuple(type(m).__name__ for m in self.model)
        pooling = next((m for m in self.model if type(m).__name__ == "Pooling"), None)
        parameter = next(self.model.parameters())
        problems = []
        if modules != self.spec.expected_modules:
            problems.append(f"modules {modules}")
        if pooling is None or getattr(pooling, "pooling_mode", None) != self.spec.expected_pooling:
            problems.append(f"pooling {getattr(pooling, 'pooling_mode', None)}")
        if self.model.get_embedding_dimension() != self.spec.expected_dimension:
            problems.append(f"dimension {self.model.get_embedding_dimension()}")
        if parameter.dtype != self._torch.float32:
            problems.append(f"dtype {parameter.dtype}")
        if parameter.device.type != "cpu":
            problems.append(f"device {parameter.device}")
        if problems:
            raise EngineConfigError("loaded model differs from the specification: " + "; ".join(problems))

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """One `model.encode` call for all texts, in the given order. Returns float32, shape (n, 768)."""
        items = _check_texts(texts)
        self.model.eval()
        with self._torch.inference_mode():
            vectors = self.model.encode(items, batch_size=self.spec.batch_size, convert_to_numpy=True, show_progress_bar=False)
        if vectors.shape != (len(items), self.spec.expected_dimension) or not np.isfinite(vectors).all():
            raise EngineConfigError(f"unexpected embeddings: shape {vectors.shape}, finite {bool(np.isfinite(vectors).all())}")
        return vectors

    def snapshot_dir(self) -> Path:
        from huggingface_hub import try_to_load_from_cache

        cached = try_to_load_from_cache(self.spec.model_id, "config.json", revision=self.spec.revision)
        if not isinstance(cached, str):
            raise EngineConfigError("the pinned revision is not in the local cache")
        return Path(cached).parent

    def weights_sha256(self) -> str:
        """SHA-256 of the cached `model.safetensors` (reads about 1 GB)."""
        digest = hashlib.sha256()
        with open(self.snapshot_dir() / "model.safetensors", "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 22), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def describe(self) -> dict:
        """Model identity and effective configuration, for results and manifests."""
        import huggingface_hub.constants as hub_constants
        import sentence_transformers
        import transformers

        transformer = self.model[0]
        return {
            **asdict(self.spec),
            "snapshot_revision": self.snapshot_dir().name,
            "modules": [type(m).__name__ for m in self.model],
            "pooling_mode": next(m for m in self.model if type(m).__name__ == "Pooling").pooling_mode,
            "embedding_dimension": self.model.get_embedding_dimension(),
            "max_seq_length": self.model.max_seq_length,
            "attention_implementation": str(getattr(transformer.auto_model.config, "_attn_implementation", "unknown")),
            "can_flatten_inputs": bool(self.model._can_flatten_inputs()),
            "torch_threads": self._torch.get_num_threads(),
            "normalize_embeddings_argument": False,
            "hf_hub_offline": bool(hub_constants.is_offline_mode()),
            "versions": {"python": platform.python_version(), "torch": self._torch.__version__, "transformers": transformers.__version__,
                         "sentence_transformers": sentence_transformers.__version__, "numpy": np.__version__},
        }
