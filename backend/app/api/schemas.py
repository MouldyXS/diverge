"""Request and response schemas of the HTTP API v1 (Pydantic). They depend on the service types, never on the engine.

Requests are strict: unknown fields are rejected and no value is coerced (a number is never turned into a string, a
string is never taken as a list). The schemas apply no semantic rule: the service owns the entry limit and the engine
owns the P0 rules and the token limit.

Responses are built from the service results by explicit conversions, so no NumPy object reaches the serializer and no
value is recomputed or rounded. The set's distance matrix is not sent: the pairs, with their 0-based indexes `i` and
`j`, determine it completely.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services import ModelInfo, ModelRef, PairResult, SetInterpretation, SetResult, interpret_set

API_VERSION = "v1"


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PairRequest(_Request):
    word_a: str
    word_b: str


class SetRequest(_Request):
    words: list[str]


class ModelRefOut(_Response):
    model_id: str
    declared_revision: str = Field(description="Revision requested in the model specification.")
    snapshot_revision: str | None = Field(description="Snapshot resolved in the local cache (a revision name, not a hash "
                                                      "of the weights); null when not reported.")

    @classmethod
    def from_ref(cls, ref: ModelRef) -> ModelRefOut:
        return cls(model_id=ref.model_id, declared_revision=ref.declared_revision, snapshot_revision=ref.snapshot_revision)


class PairResponse(_Response):
    word_a: str = Field(description="Normalized form of the first word.")
    word_b: str = Field(description="Normalized form of the second word.")
    similarity: float = Field(description="Cosine similarity, in [-1, 1].")
    distance: float = Field(description="Cosine distance, 1 - similarity, in [0, 2].")
    model: ModelRefOut

    @classmethod
    def from_result(cls, result: PairResult) -> PairResponse:
        analysis = result.analysis
        return cls(word_a=analysis.word_a, word_b=analysis.word_b, similarity=analysis.similarity,
                   distance=analysis.distance, model=ModelRefOut.from_ref(result.model))


class PairScoreOut(_Response):
    i: int = Field(description="0-based index of the first word in `words`; i < j.")
    j: int = Field(description="0-based index of the second word in `words`.")
    word_i: str
    word_j: str
    similarity: float
    distance: float

    @classmethod
    def from_score(cls, score) -> PairScoreOut:
        return cls(i=score.i, j=score.j, word_i=score.word_i, word_j=score.word_j, similarity=score.similarity,
                   distance=score.distance)


InterpretationFlag = Literal["single_pair", "all_equal_at_precision", "all_exactly_equal", "tie_at_min", "exact_tie_at_min",
                             "tie_at_max", "exact_tie_at_max"]
InterpretationNote = Literal["relative_to_this_set", "no_reference_distribution", "mean_is_experimental"]


class PairRefOut(_Response):
    i: int = Field(description="0-based index of the first word in `words`; i < j.")
    j: int = Field(description="0-based index of the second word in `words`.")


class SetInterpretationOut(_Response):
    """Structured facts about the distribution of a set's distances: numbers, pair indexes and codes, no sentences.

    Comparisons use the four-decimal values the interface shows, so a tie always matches the screen. Every statement
    is relative to this set; none is a classification and none refers to a reference distribution.
    """

    version: int = Field(description="Version of the interpretation rules.")
    precision_decimals: int = Field(description="Decimals at which values are compared (those the interface shows).")
    n_pairs: int
    min_distance: float = Field(description="Smallest pair distance, exact.")
    max_distance: float = Field(description="Largest pair distance, exact.")
    range: float = Field(description="max_distance - min_distance.")
    min_pairs: list[PairRefOut] = Field(description="Pairs equal to the smallest distance at the shown precision, at most "
                                                    "five; the first is `closest`.")
    max_pairs: list[PairRefOut] = Field(description="Pairs equal to the largest distance at the shown precision, at most "
                                                    "five; the first is `most_distant`.")
    n_min_pairs: int = Field(description="Total pairs tied at the smallest distance (may exceed the listed ones).")
    n_max_pairs: int = Field(description="Total pairs tied at the largest distance.")
    n_above_mean: int = Field(description="Pairs whose shown distance is above the shown mean.")
    n_below_mean: int
    n_at_mean: int = Field(description="Pairs equal to the mean at the shown precision.")
    flags: list[InterpretationFlag] = Field(description="Edge cases.")
    notes: list[InterpretationNote] = Field(description="Fixed methodological warnings, by code.")

    @classmethod
    def from_interpretation(cls, interpretation: SetInterpretation) -> SetInterpretationOut:
        return cls(
            version=interpretation.version, precision_decimals=interpretation.precision_decimals,
            n_pairs=interpretation.n_pairs, min_distance=interpretation.min_distance, max_distance=interpretation.max_distance,
            range=interpretation.range, min_pairs=[PairRefOut(i=ref.i, j=ref.j) for ref in interpretation.min_pairs],
            max_pairs=[PairRefOut(i=ref.i, j=ref.j) for ref in interpretation.max_pairs],
            n_min_pairs=interpretation.n_min_pairs, n_max_pairs=interpretation.n_max_pairs,
            n_above_mean=interpretation.n_above_mean, n_below_mean=interpretation.n_below_mean,
            n_at_mean=interpretation.n_at_mean, flags=list(interpretation.flags), notes=list(interpretation.notes),
        )


class SetResponse(_Response):
    words: list[str] = Field(description="Normalized words, in entry order.")
    n_words: int
    n_pairs: int = Field(description="n(n - 1) / 2.")
    pairs: list[PairScoreOut] = Field(description="Every pair, i < j, in combinations order.")
    mean_distance: float = Field(description="Mean cosine distance of the pairs, unscaled. An experimental indicator, "
                                             "not a measure of creativity or of any cognitive ability.")
    closest: PairScoreOut
    most_distant: PairScoreOut
    interpretation: SetInterpretationOut
    model: ModelRefOut

    @classmethod
    def from_result(cls, result: SetResult, interpretation: SetInterpretation | None = None) -> SetResponse:
        """`interpretation` is computed by the route after the analysis; when omitted it is computed here, identically."""
        analysis = result.analysis
        interpretation = interpret_set(result) if interpretation is None else interpretation
        return cls(words=list(analysis.words), n_words=len(analysis.words), n_pairs=analysis.n_pairs,
                   pairs=[PairScoreOut.from_score(score) for score in analysis.pairs], mean_distance=analysis.mean_distance,
                   closest=PairScoreOut.from_score(analysis.closest),
                   most_distant=PairScoreOut.from_score(analysis.most_distant),
                   interpretation=SetInterpretationOut.from_interpretation(interpretation), model=ModelRefOut.from_ref(result.model))


class LimitsOut(_Response):
    max_words: int = Field(description="Entries per set request (service limit).")
    max_input_tokens: int = Field(description="Tokens per entry, special tokens included (model context).")


class VersionsOut(_Response):
    python: str | None = None
    torch: str | None = None
    transformers: str | None = None
    sentence_transformers: str | None = None
    numpy: str | None = None


# Public field <- source. Identity and limits come from typed service objects and are required; the rest are
# informative keys of `ModelInfo.description` (the embedder's describe()) and are null when absent or mistyped.
MODEL_DESCRIPTION_FIELDS: dict[str, tuple[str, type]] = {
    "embedding_dimension": ("embedding_dimension", int),
    "pooling_mode": ("pooling_mode", str),
    "modules": ("modules", tuple),
    "device": ("device", str),
    "dtype": ("dtype", str),
    "attention_implementation": ("attention_implementation", str),
    "batch_size": ("batch_size", int),
    "offline": ("hf_hub_offline", bool),
}
VERSION_KEYS = ("python", "torch", "transformers", "sentence_transformers", "numpy")


def _optional(description: Mapping[str, Any], key: str, kind: type) -> Any:
    value = description.get(key)
    if kind is int and isinstance(value, bool):
        return None
    if kind is tuple:
        return list(value) if isinstance(value, tuple) and all(isinstance(item, str) for item in value) else None
    return value if isinstance(value, kind) else None


class ModelResponse(_Response):
    model_id: str
    declared_revision: str
    snapshot_revision: str | None = Field(description="Snapshot resolved in the local cache, not a hash of the weights.")
    embedding_dimension: int | None
    pooling_mode: str | None
    modules: list[str] | None
    device: str | None
    dtype: str | None
    attention_implementation: str | None
    batch_size: int | None = Field(description="Internal encoding batch size; not a request limit.")
    offline: bool | None = Field(description="Hugging Face offline mode as reported by the engine.")
    limits: LimitsOut
    versions: VersionsOut
    api_version: str

    @classmethod
    def from_info(cls, info: ModelInfo) -> ModelResponse:
        """Built once at startup from the stored metadata; reads neither the disk nor the embedder."""
        description = info.description
        versions = description.get("versions")
        versions = versions if isinstance(versions, Mapping) else {}
        return cls(
            model_id=info.ref.model_id, declared_revision=info.ref.declared_revision,
            snapshot_revision=info.ref.snapshot_revision,
            **{field: _optional(description, key, kind) for field, (key, kind) in MODEL_DESCRIPTION_FIELDS.items()},
            limits=LimitsOut(max_words=info.limits.max_words, max_input_tokens=info.limits.max_input_tokens),
            versions=VersionsOut(**{key: versions[key] if isinstance(versions.get(key), str) else None for key in VERSION_KEYS}),
            api_version=API_VERSION,
        )


class HealthResponse(_Response):
    status: str = Field(description="Service state: ready, failed or stopping.")


class ErrorResponse(_Response):
    request_id: str | None
    code: str
    message: str
    details: dict[str, Any]
