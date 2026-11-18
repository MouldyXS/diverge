// Responses with the exact shape of backend/app/api/schemas.py. The words are neutral test words.
import type { ModelResponse, PairResponse, SetResponse } from "../api/types";

export const modelRef = {
  model_id: "ibm-granite/granite-embedding-278m-multilingual",
  declared_revision: "a9cb5338491faf32b73dd17b714a31821c021bbf",
  snapshot_revision: "a9cb5338491faf32b73dd17b714a31821c021bbf",
};

export const modelResponse: ModelResponse = {
  ...modelRef,
  embedding_dimension: 768,
  pooling_mode: "cls",
  modules: ["Transformer", "Pooling", "Normalize"],
  device: "cpu",
  dtype: "float32",
  attention_implementation: "sdpa",
  batch_size: 32,
  offline: true,
  limits: { max_words: 5, max_input_tokens: 512 },
  versions: { python: "3.12.10", torch: "2.15.0+cpu", transformers: "5.22.1", sentence_transformers: "6.2.0", numpy: "2.5.4" },
  api_version: "v1",
};

export const pairResponse: PairResponse = {
  word_a: "casa",
  word_b: "perro",
  similarity: 0.7431632916387285,
  distance: 0.2568367083612715,
  model: modelRef,
};

export const setResponse: SetResponse = {
  words: ["guerra", "paz", "noche"],
  n_words: 3,
  n_pairs: 3,
  pairs: [
    { i: 0, j: 1, word_i: "guerra", word_j: "paz", similarity: 0.8185123456789012, distance: 0.18148765432109876 },
    { i: 0, j: 2, word_i: "guerra", word_j: "noche", similarity: 0.7012345678901234, distance: 0.2987654321098766 },
    { i: 1, j: 2, word_i: "paz", word_j: "noche", similarity: 0.7240000000000001, distance: 0.2759999999999999 },
  ],
  mean_distance: 0.2520843547469884,
  closest: { i: 0, j: 1, word_i: "guerra", word_j: "paz", similarity: 0.8185123456789012, distance: 0.18148765432109876 },
  most_distant: { i: 0, j: 2, word_i: "guerra", word_j: "noche", similarity: 0.7012345678901234, distance: 0.2987654321098766 },
  // Exactly what backend `interpret_set` returns for these three pairs.
  interpretation: {
    version: 1,
    precision_decimals: 4,
    n_pairs: 3,
    min_distance: 0.18148765432109876,
    max_distance: 0.2987654321098766,
    range: 0.11727777778877785,
    min_pairs: [{ i: 0, j: 1 }],
    max_pairs: [{ i: 0, j: 2 }],
    n_min_pairs: 1,
    n_max_pairs: 1,
    n_above_mean: 2,
    n_below_mean: 1,
    n_at_mean: 0,
    flags: [],
    notes: ["relative_to_this_set", "no_reference_distribution", "mean_is_experimental"],
  },
  model: modelRef,
};

export const requestId = "3f2b8c1e-6d4a-4e7f-9b0c-2a5d8e1f4c76";

export function errorBody(code: string, details: Record<string, unknown> = {}, id: string | null = requestId) {
  return { request_id: id, code, message: "Fixed English text.", details };
}

/** A fetch stub answering with a JSON body (or raw text), recording every call. */
export function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  return new Response(text, {
    status,
    headers: { "Content-Type": typeof body === "string" ? "text/plain" : "application/json", "X-Request-ID": requestId, ...headers },
  });
}
