import { describe, expect, test } from "vitest";

import type { PairScoreOut } from "../api/types";
import { setResponse } from "../test/fixtures";
import { buildMatrix, distanceRange, MatrixIntegrityError, scaleColor, scalePosition, SCALE_HIGH, SCALE_LOW } from "./matrix";

function result(words: string[], pairs: PairScoreOut[]) {
  return { words, n_words: words.length, pairs, n_pairs: pairs.length };
}

function allPairs(n: number): PairScoreOut[] {
  const pairs: PairScoreOut[] = [];
  for (let i = 0; i < n; i += 1) {
    for (let j = i + 1; j < n; j += 1) {
      pairs.push({ i, j, word_i: `w${i}`, word_j: `w${j}`, similarity: 1 - (i * 100 + j) / 10_000, distance: (i * 100 + j) / 10_000 });
    }
  }
  return pairs;
}

describe("buildMatrix", () => {
  test("is symmetric, keeps the exact values and leaves the diagonal null", () => {
    const matrix = buildMatrix(setResponse);
    expect(matrix).toEqual([
      [null, 0.18148765432109876, 0.2987654321098766],
      [0.18148765432109876, null, 0.2759999999999999],
      [0.2987654321098766, 0.2759999999999999, null],
    ]);
  });

  test("handles 32 words and their 496 pairs", () => {
    const words = Array.from({ length: 32 }, (_, k) => `w${k}`);
    const pairs = allPairs(32);
    expect(pairs).toHaveLength(496);
    const matrix = buildMatrix(result(words, pairs));
    for (const pair of pairs) {
      expect(matrix[pair.i]![pair.j]).toBe(pair.distance);
      expect(matrix[pair.j]![pair.i]).toBe(pair.distance);
    }
    expect(matrix.every((row, k) => row[k] === null)).toBe(true);
  });

  test.each([
    ["duplicated pair", result(["a", "b", "c"], [setResponse.pairs[0]!, setResponse.pairs[0]!, setResponse.pairs[2]!])],
    ["reversed indexes", result(["a", "b"], [{ ...setResponse.pairs[0]!, i: 1, j: 0 }])],
    ["index out of range", result(["a", "b"], [{ ...setResponse.pairs[0]!, i: 0, j: 2 }])],
    ["same index twice", result(["a", "b"], [{ ...setResponse.pairs[0]!, i: 1, j: 1 }])],
    ["missing pair", { words: ["a", "b", "c"], n_words: 3, pairs: setResponse.pairs.slice(0, 2), n_pairs: 3 }],
    ["n_pairs not n(n-1)/2", { words: ["a", "b", "c"], n_words: 3, pairs: setResponse.pairs.slice(0, 2), n_pairs: 2 }],
    ["n_words mismatch", { ...setResponse, n_words: 4 }],
    ["non-finite distance", result(["a", "b"], [{ ...setResponse.pairs[0]!, distance: Number.NaN }])],
  ])("rejects an incoherent response: %s", (_name, bad) => {
    expect(() => buildMatrix(bad)).toThrow(MatrixIntegrityError);
  });
});

describe("color scale", () => {
  test("is relative to the set, from its minimum to its maximum", () => {
    const range = distanceRange(setResponse.pairs);
    expect(range).toEqual({ min: 0.18148765432109876, max: 0.2987654321098766, uniform: false });
    expect(scaleColor(range.min, range)).toBe(SCALE_LOW);
    expect(scaleColor(range.max, range)).toBe(SCALE_HIGH);
    expect(scalePosition(0.24, range)).toBeGreaterThan(0);
    expect(scalePosition(0.24, range)).toBeLessThan(1);
  });

  test("equal distances give one uniform color without dividing by zero", () => {
    const pairs = allPairs(3).map((pair) => ({ ...pair, distance: 0.25 }));
    const range = distanceRange(pairs);
    expect(range.uniform).toBe(true);
    expect(scalePosition(0.25, range)).toBe(0.5);
    expect(new Set(pairs.map((pair) => scaleColor(pair.distance, range))).size).toBe(1);
    expect(scaleColor(0.25, range)).toMatch(/^#[0-9a-f]{6}$/);
  });
});
