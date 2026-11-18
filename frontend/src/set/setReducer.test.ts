import { expect, test } from "vitest";

import { setResponse } from "../test/fixtures";
import { initialSet, setReducer, splitLines } from "./setReducer";

test("pasted text is split by line breaks only, keeping inner empty lines and spaces", () => {
  expect(splitLines("casa\r\nperro\ngato\rsol")).toEqual(["casa", "perro", "gato", "sol"]);
  expect(splitLines("casa\n\nperro\n")).toEqual(["casa", "", "perro"]);
  expect(splitLines("casa\r\n")).toEqual(["casa"]);
  expect(splitLines(" dos palabras \n  casa")).toEqual([" dos palabras ", "  casa"]); // no trim, no split by spaces
  expect(splitLines("casa\n\n")).toEqual(["casa", ""]); // only the final separator's empty line is dropped
  expect(splitLines("casa")).toEqual(["casa"]);
});

test("starts with three empty rows", () => {
  const state = initialSet();
  expect(state.rows.map((row) => row.value)).toEqual(["", "", ""]);
});

test("pasting replaces the rows with the lines", () => {
  let state = setReducer(initialSet(), { type: "openPaste" });
  state = setReducer(state, { type: "pasteText", value: "uno\r\n\r\ndos\n" });
  state = setReducer(state, { type: "applyPaste" });
  expect(state.rows.map((row) => row.value)).toEqual(["uno", "", "dos"]);
  expect(new Set(state.rows.map((row) => row.id)).size).toBe(3);
  expect(state.pasteOpen).toBe(false);
});

test("editing, adding or removing rows withdraws the previous result", () => {
  const withResult = { ...initialSet(), status: "success" as const, result: setResponse };
  for (const action of [{ type: "edit", id: 0, value: "x" }, { type: "add" }, { type: "remove", id: 1 }] as const) {
    const next = setReducer(withResult, action);
    expect(next.result).toBeNull();
    expect(next.withdrawn).toBe(true);
  }
});

test("rows cannot change while their analysis runs", () => {
  const loading = setReducer(initialSet(), { type: "submit" });
  expect(setReducer(loading, { type: "add" })).toBe(loading);
  expect(setReducer(loading, { type: "edit", id: 0, value: "x" })).toBe(loading);
});
