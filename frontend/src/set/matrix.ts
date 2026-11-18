// Rebuilds the distance matrix from the pairs of a SetResponse. Pure functions; no value is recomputed or rounded.
import type { PairScoreOut, SetResponse } from "../api/types";

export type Matrix = (number | null)[][];

export class MatrixIntegrityError extends Error {
  constructor(reason: string) {
    super(`matrix integrity: ${reason}`);
    this.name = "MatrixIntegrityError";
  }
}

/**
 * An n x n symmetric matrix with m[i][j] = m[j][i] = pair.distance and a null diagonal ("not applicable").
 * Throws MatrixIntegrityError when the response does not describe exactly one distance per pair.
 */
export function buildMatrix(result: Pick<SetResponse, "words" | "n_words" | "pairs" | "n_pairs">): Matrix {
  const n = result.words.length;
  if (n !== result.n_words) {
    throw new MatrixIntegrityError("words.length differs from n_words");
  }
  if (result.n_pairs !== (n * (n - 1)) / 2 || result.pairs.length !== result.n_pairs) {
    throw new MatrixIntegrityError("the number of pairs is not n(n - 1) / 2");
  }
  const matrix: Matrix = Array.from({ length: n }, () => Array.from({ length: n }, () => null));
  for (const pair of result.pairs) {
    const { i, j, distance } = pair;
    if (!Number.isInteger(i) || !Number.isInteger(j) || i < 0 || !(i < j) || j >= n) {
      throw new MatrixIntegrityError("a pair has invalid indexes");
    }
    if (typeof distance !== "number" || !Number.isFinite(distance)) {
      throw new MatrixIntegrityError("a pair has no finite distance");
    }
    const row = matrix[i]!;
    if (row[j] !== null) {
      throw new MatrixIntegrityError("a pair appears more than once");
    }
    row[j] = distance;
    matrix[j]![i] = distance;
  }
  return matrix;
}

export interface Range {
  min: number;
  max: number;
  uniform: boolean;
}

export function distanceRange(pairs: PairScoreOut[]): Range {
  const values = pairs.map((pair) => pair.distance);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, max, uniform: min === max };
}

// Must equal --scale-low and --scale-high in styles/tokens.css (checked by a test).
export const SCALE_LOW = "#e6f2f3";
export const SCALE_HIGH = "#5e9aa1";

function channels(hex: string): [number, number, number] {
  return [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16)) as [number, number, number];
}

/** Position of a value in the scale relative to the current set, in [0, 1]; 0.5 for every value if they are all equal. */
export function scalePosition(value: number, range: Range): number {
  if (range.uniform) {
    return 0.5;
  }
  return Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
}

export function scaleColor(value: number, range: Range): string {
  const t = scalePosition(value, range);
  const [low, high] = [channels(SCALE_LOW), channels(SCALE_HIGH)];
  const mixed = low.map((c, k) => Math.round(c + (high[k]! - c) * t));
  return `#${mixed.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}
