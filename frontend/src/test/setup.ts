import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, vi } from "vitest";

// The application must never write entries or results to the console.
const consoleMethods = ["log", "info", "debug", "warn", "error"] as const;
let spies: ReturnType<typeof vi.spyOn>[] = [];

beforeEach(() => {
  spies = consoleMethods.map((method) => vi.spyOn(console, method));
});

afterEach(() => {
  cleanup();
  for (const spy of spies) {
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  }
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
