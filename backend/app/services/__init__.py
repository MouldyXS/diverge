"""Service layer (stage 3B.6): `AnalysisService` between the engine and a future API. No HTTP dependencies."""

from .analysis import (DEFAULT_MAX_WORDS, AnalysisService, ModelInfo, ModelRef, PairResult, ServiceLimits, ServiceState,
                       SetResult)
from .errors import (SAFE_REASONS, UNRECOGNIZED_REASON, AnalysisBusy, EntriesRejected, EntryIssue, ServiceError,
                     ServiceUnavailable, TooManyWords)
from .interpretation import InterpretationError, PairRef, SetInterpretation, interpret_set

__all__ = [
    "DEFAULT_MAX_WORDS", "SAFE_REASONS", "UNRECOGNIZED_REASON", "AnalysisBusy", "AnalysisService", "EntriesRejected",
    "EntryIssue", "InterpretationError", "ModelInfo", "ModelRef", "PairRef", "PairResult", "ServiceError", "ServiceLimits",
    "ServiceState", "ServiceUnavailable", "SetInterpretation", "SetResult", "TooManyWords", "interpret_set",
]
