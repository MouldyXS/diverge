import { fireEvent, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { renderApp } from "./test/render";

test("renders the title, the backend state and the two modes", async () => {
  await renderApp();
  expect(screen.getByRole("heading", { level: 1, name: "Diverge" })).toBeTruthy();
  expect(screen.getByText("Disponible")).toBeTruthy();
  expect(screen.getAllByRole("tab")).toHaveLength(2);
});

test("tabs follow the keyboard pattern: arrows, Home and End move selection and focus", async () => {
  await renderApp();
  const [pair, set] = screen.getAllByRole("tab") as [HTMLElement, HTMLElement];
  expect(pair.getAttribute("aria-selected")).toBe("true");
  expect([pair.tabIndex, set.tabIndex]).toEqual([0, -1]);
  pair.focus();
  fireEvent.keyDown(pair, { key: "ArrowRight" });
  expect(set.getAttribute("aria-selected")).toBe("true");
  expect(document.activeElement).toBe(set);
  expect(document.getElementById("panel-pair")!.hidden).toBe(true);
  expect(document.getElementById("panel-set")!.hidden).toBe(false);
  fireEvent.keyDown(set, { key: "ArrowRight" });
  expect(document.activeElement).toBe(pair); // wraps around
  fireEvent.keyDown(pair, { key: "End" });
  expect(document.activeElement).toBe(set);
  fireEvent.keyDown(set, { key: "Home" });
  expect(document.activeElement).toBe(pair);
});

test("every input has an accessible label", async () => {
  await renderApp();
  for (const input of Array.from(document.querySelectorAll("input"))) {
    const labelled = input.getAttribute("aria-label") || (input.id && document.querySelector(`label[for="${input.id}"]`));
    expect(labelled, input.id).toBeTruthy();
  }
});

test("the application stores nothing and puts no words in the URL", async () => {
  await renderApp();
  expect(window.localStorage.length).toBe(0);
  expect(window.sessionStorage.length).toBe(0);
  expect(window.location.search).toBe("");
});
