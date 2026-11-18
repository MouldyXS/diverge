// Contracts of the Diverge HTTP API v1, copied from backend/app/api/schemas.py and backend/app/api/errors.py.
// Nothing here is computed by the frontend; every value comes from the backend unchanged.

export interface PairRequest {
  word_a: string;
  word_b: string;
}

export interface SetRequest {
  words: string[];
}

export interface ModelRefOut {
  model_id: string;
  declared_revision: string;
  /** Snapshot resolved in the backend's local cache (a revision name, not a hash of the weights); null when not reported. */
  snapshot_revision: string | null;
}

export interface PairResponse {
  /** Normalized forms returned by the engine. */
  word_a: string;
  word_b: string;
  /** Cosine similarity, in [-1, 1]. */
  similarity: number;
  /** Cosine distance, 1 - similarity, in [0, 2]. */
  distance: number;
  model: ModelRefOut;
}

export interface PairScoreOut {
  /** 0-based indexes into `SetResponse.words`; i < j. */
  i: number;
  j: number;
  word_i: string;
  word_j: string;
  similarity: number;
  distance: number;
}

/** A pair by the 0-based indexes of its words in `SetResponse.words`; i < j. */
export interface PairRef {
  i: number;
  j: number;
}

export const INTERPRETATION_FLAGS = [
  "single_pair",
  "all_equal_at_precision",
  "all_exactly_equal",
  "tie_at_min",
  "exact_tie_at_min",
  "tie_at_max",
  "exact_tie_at_max",
] as const;
export type InterpretationFlag = (typeof INTERPRETATION_FLAGS)[number];

export const INTERPRETATION_NOTES = ["relative_to_this_set", "no_reference_distribution", "mean_is_experimental"] as const;
export type InterpretationNote = (typeof INTERPRETATION_NOTES)[number];

/**
 * Facts about the distribution of a set's distances: numbers, pair indexes and codes, never sentences. Values are compared
 * at `precision_decimals` (the decimals the interface shows), so a tie always matches the screen.
 */
export interface SetInterpretation {
  version: number;
  precision_decimals: number;
  n_pairs: number;
  /** Exact smallest and largest distance, and their difference. */
  min_distance: number;
  max_distance: number;
  range: number;
  /** Pairs equal to the smallest (largest) distance at the shown precision, at most five; the first is `closest` (`most_distant`). */
  min_pairs: PairRef[];
  max_pairs: PairRef[];
  /** Totals tied at the extreme, which may exceed the listed pairs. */
  n_min_pairs: number;
  n_max_pairs: number;
  n_above_mean: number;
  n_below_mean: number;
  /** Equal to the mean at the shown precision. */
  n_at_mean: number;
  flags: InterpretationFlag[];
  notes: InterpretationNote[];
}

export interface SetResponse {
  words: string[];
  n_words: number;
  /** n(n - 1) / 2. */
  n_pairs: number;
  pairs: PairScoreOut[];
  /** Mean cosine distance, unscaled: an experimental indicator, not a measure of creativity. */
  mean_distance: number;
  closest: PairScoreOut;
  most_distant: PairScoreOut;
  interpretation: SetInterpretation;
  model: ModelRefOut;
}

export interface ModelResponse {
  model_id: string;
  declared_revision: string;
  snapshot_revision: string | null;
  embedding_dimension: number | null;
  pooling_mode: string | null;
  modules: string[] | null;
  device: string | null;
  dtype: string | null;
  attention_implementation: string | null;
  batch_size: number | null;
  offline: boolean | null;
  limits: { max_words: number; max_input_tokens: number };
  versions: {
    python: string | null;
    torch: string | null;
    transformers: string | null;
    sentence_transformers: string | null;
    numpy: string | null;
  };
  api_version: string;
}

export type ServiceStatus = "ready" | "failed" | "stopping";

export interface HealthResponse {
  status: ServiceStatus;
}

export const ERROR_CODES = [
  "request_invalid",
  "invalid_entries",
  "too_few_words",
  "too_many_words",
  "analysis_busy",
  "service_unavailable",
  "payload_too_large",
  "not_found",
  "method_not_allowed",
  "internal_error",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

export const REASONS = [
  "empty",
  "multiple_words",
  "digit_or_symbol",
  "duplicate",
  "exceeds_model_context",
  "unrecognized_reason",
] as const;
export type Reason = (typeof REASONS)[number];

export interface EntryIssue {
  /** 1-based position of the entry, as sent. */
  position: number;
  reasons: Reason[];
  tokens: number | null;
  max_tokens: number | null;
}

export interface ErrorResponse {
  request_id: string | null;
  code: ErrorCode;
  /** Fixed English text for developers; never shown to the user. */
  message: string;
  details: Record<string, unknown>;
}
