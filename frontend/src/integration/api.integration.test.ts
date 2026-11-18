// Run with `npm run test:integration` against a running Diverge API (VITE_DIVERGE_API_BASE_URL, default
// http://127.0.0.1:8000/api/v1). It checks the shapes of the real responses against the TypeScript contracts, not the
// numbers, so the backend may use a synthetic embedder. It is not part of `npm test`.
import { describe, expect, test } from "vitest";

import { analyzePair, analyzeSet, API_BASE_URL, getHealth, getModel } from "../api/client";
import { ApiError, entryIssues, tooManyWordsDetails } from "../api/errors";
import type { PairScoreOut } from "../api/types";
import { describeSet } from "../interpretation/describe";
import { buildMatrix } from "../set/matrix";

const keys = (value: object) => Object.keys(value).sort();
const MODEL_REF = ["declared_revision", "model_id", "snapshot_revision"];
const PAIR_SCORE = ["distance", "i", "j", "similarity", "word_i", "word_j"];

function isPairScore(pair: PairScoreOut) {
  expect(keys(pair)).toEqual(PAIR_SCORE);
  expect(Number.isInteger(pair.i) && Number.isInteger(pair.j) && pair.i < pair.j).toBe(true);
  expect(typeof pair.similarity === "number" && typeof pair.distance === "number").toBe(true);
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("expected a rejection");
}

describe(`Diverge API at ${API_BASE_URL}`, () => {
  test("health", async () => {
    expect(["ready", "failed", "stopping"]).toContain((await getHealth()).status);
  });

  test("model metadata has exactly the contract's fields", async () => {
    const model = await getModel();
    expect(keys(model)).toEqual([
      "api_version", "attention_implementation", "batch_size", "declared_revision", "device", "dtype", "embedding_dimension",
      "limits", "model_id", "modules", "offline", "pooling_mode", "snapshot_revision", "versions",
    ]);
    expect(keys(model.limits)).toEqual(["max_input_tokens", "max_words"]);
    expect(keys(model.versions)).toEqual(["numpy", "python", "sentence_transformers", "torch", "transformers"]);
    expect(Number.isInteger(model.limits.max_words) && Number.isInteger(model.limits.max_input_tokens)).toBe(true);
    expect(model.snapshot_revision === null || typeof model.snapshot_revision === "string").toBe(true);
  });

  test("pair analysis", async () => {
    const result = await analyzePair({ word_a: " Casa", word_b: "perro" });
    expect(keys(result)).toEqual(["distance", "model", "similarity", "word_a", "word_b"]);
    expect(keys(result.model)).toEqual(MODEL_REF);
    expect(result.word_a).toBe("casa");
    expect(result.distance).toBeCloseTo(1 - result.similarity, 12);
  });

  test("set analysis rebuilds into a coherent matrix", async () => {
    const result = await analyzeSet({ words: ["casa", "hogar", "edificio", "nube"] });
    expect(keys(result)).toEqual(["closest", "interpretation", "mean_distance", "model", "most_distant", "n_pairs", "n_words", "pairs", "words"]);
    const it = result.interpretation;
    expect(keys(it)).toEqual([
      "flags", "max_distance", "max_pairs", "min_distance", "min_pairs", "n_above_mean", "n_at_mean", "n_below_mean", "n_max_pairs",
      "n_min_pairs", "n_pairs", "notes", "precision_decimals", "range", "version",
    ]);
    expect([it.version, it.precision_decimals, it.n_pairs]).toEqual([1, 4, 6]);
    expect([it.min_pairs[0]!.i, it.min_pairs[0]!.j]).toEqual([result.closest.i, result.closest.j]);
    expect([it.max_pairs[0]!.i, it.max_pairs[0]!.j]).toEqual([result.most_distant.i, result.most_distant.j]);
    expect(it.n_above_mean + it.n_below_mean + it.n_at_mean).toBe(6);
    expect(it.notes).toEqual(["relative_to_this_set", "no_reference_distribution", "mean_is_experimental"]);
    expect(describeSet(result).length).toBeGreaterThanOrEqual(4); // the sentences are written from the real response
    result.pairs.forEach(isPairScore);
    isPairScore(result.closest);
    isPairScore(result.most_distant);
    expect([result.n_words, result.n_pairs]).toEqual([4, 6]);
    const matrix = buildMatrix(result);
    expect(matrix[0]![1]).toBe(result.pairs[0]!.distance);
    expect(matrix[1]![1]).toBeNull();
  });

  test("errors follow ErrorResponse, with positions, codes and a request ID", async () => {
    const invalid = await rejection(analyzeSet({ words: ["casa", "", "dos palabras", "casa"] }));
    expect([invalid.kind, invalid.status, invalid.code]).toEqual(["http", 422, "invalid_entries"]);
    expect(entryIssues(invalid).map((issue) => [issue.position, issue.reasons])).toEqual([
      [2, ["empty"]],
      [3, ["multiple_words"]],
      [4, ["duplicate"]],
    ]);
    expect(invalid.requestId).toMatch(/^[0-9a-f-]{36}$/);
    const few = await rejection(analyzeSet({ words: ["solitaria"] }));
    expect(few.code).toBe("too_few_words");
    const max = (await getModel()).limits.max_words;
    const many = await rejection(analyzeSet({ words: Array.from({ length: max + 1 }, (_, k) => `w${String.fromCharCode(97 + (k % 26))}${k}`) }));
    expect(tooManyWordsDetails(many)).toEqual({ maxWords: max, receivedAtLeast: max + 1 });
  });
});
