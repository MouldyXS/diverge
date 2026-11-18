import { expect, test } from "vitest";

import scoring from "../../docs/scoring.md?raw";
import tokens from "./styles/tokens.css?raw";
import { ERROR_CODES, REASONS } from "./api/types";
import { copy, P0_NOTICE } from "./copy";

test("the P0 notice is the literal text of docs/scoring.md section 8", () => {
  const section = scoring.split("## 8. User notice under P0")[1]!.split("\n## ")[0]!;
  const paragraphs = section
    .split("\n")
    .filter((line) => line.startsWith(">"))
    .map((line) => line.replace(/^>\s?/, ""))
    .join("\n")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim());
  expect(paragraphs).toEqual([...P0_NOTICE]);
});

test("every error code and reason has a Spanish text", () => {
  for (const code of ERROR_CODES) {
    expect(copy.errors.codes[code].length).toBeGreaterThan(0);
  }
  for (const reason of REASONS) {
    expect(copy.reasons[reason].length).toBeGreaterThan(0);
  }
});

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (high + 0.05) / (low + 0.05);
}

test("text colors meet WCAG AA (4.5:1) on the backgrounds they are used on", () => {
  const color = (name: string) => tokens.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`))![1]!;
  const pairs: [string, string][] = [
    ["text", "background"], ["text", "surface"], ["text-secondary", "background"], ["text-secondary", "surface"],
    ["accent", "surface"], ["error", "surface"], ["warning", "surface"], ["success", "surface"],
    ["text", "scale-low"], ["text", "scale-high"], ["text-secondary", "accent-soft"],
  ];
  for (const [fg, bg] of pairs) {
    expect(contrast(color(fg), color(bg)), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
  }
  expect(contrast("#ffffff", color("accent")), "white on accent").toBeGreaterThanOrEqual(4.5);
});

test("the matrix colors used in code are the design tokens", async () => {
  const { SCALE_LOW, SCALE_HIGH } = await import("./set/matrix");
  expect(tokens).toContain(`--scale-low: ${SCALE_LOW};`);
  expect(tokens).toContain(`--scale-high: ${SCALE_HIGH};`);
});
