"""Diverge semantic engine (D21). Pure Python: no FastAPI imports, and the model is optional.

* `normalize`, `validation`: entry normalization, the deterministic P0 rules and the model-context check.
* `distances`: cosine similarity and distance on vectors (NumPy only).
* `embedder`: model specification, the `Embedder` interface and `GraniteEmbedder` (loads torch lazily).
* `analysis`: pair analysis (main unit) and set analysis (all pairs; mean distance as an experimental indicator).
* `protocol`: DAT7, historical and optional.
"""

from .analysis import PairAnalysis, PairScore, SetAnalysis, analyze_pair, analyze_set, analyze_vectors
from .distances import Pairwise, cosine_distance, cosine_similarity, pairwise
from .embedder import REFERENCE_MODEL, Embedder, GraniteEmbedder, ModelSpec
from .errors import EngineConfigError, EngineError, EngineInputError, EngineValidationError
from .normalize import normalize
from .protocol import Dat7Result, Dat7Selection, analyze_dat7, dat7_index, select_dat7
from .validation import EXCEEDS_MODEL_CONTEXT, EntryCheck, EntryReport, LengthCheck, check_entries, check_lengths, validate_entries

__all__ = [
    "EXCEEDS_MODEL_CONTEXT", "REFERENCE_MODEL", "Dat7Result", "Dat7Selection", "Embedder", "EngineConfigError", "EngineError",
    "EngineInputError", "EngineValidationError", "EntryCheck", "EntryReport", "GraniteEmbedder", "LengthCheck", "ModelSpec",
    "PairAnalysis", "PairScore", "Pairwise", "SetAnalysis", "analyze_dat7", "analyze_pair", "analyze_set", "analyze_vectors",
    "check_entries", "check_lengths", "cosine_distance", "cosine_similarity", "dat7_index", "normalize", "pairwise",
    "select_dat7", "validate_entries",
]
