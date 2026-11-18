import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { P0_NOTICE } from "../copy";
import { errorBody, jsonResponse, pairResponse } from "../test/fixtures";
import { deferred, renderApp } from "../test/render";

function fill(a: string, b: string) {
  fireEvent.change(screen.getByLabelText("Concepto A"), { target: { value: a } });
  fireEvent.change(screen.getByLabelText("Concepto B"), { target: { value: b } });
}

const submit = () => screen.getByRole("button", { name: "Analizar pareja" });

test("sends the words exactly as typed and shows the result with the P0 notice", async () => {
  const server = await renderApp({ "/pairs": [jsonResponse(200, pairResponse)] });
  expect(submit()).toHaveProperty("disabled", true); // both fields are empty
  fill(" Casa ", "PERRO");
  fireEvent.click(submit());
  const result = await screen.findByRole("region", { name: "Resultado" });
  expect(server.calls.find((c) => c.path === "/pairs")!.body).toEqual({ word_a: " Casa ", word_b: "PERRO" });
  expect(within(result).getByText("casa")).toBeTruthy(); // normalized words from the API
  expect(within(result).getByText("0,7432")).toBeTruthy();
  expect(within(result).getByText("0,2568").getAttribute("title")).toBe("0.2568367083612715");
  expect(within(result).getByText(P0_NOTICE[0])).toBeTruthy();
  expect(within(result).getAllByText(pairResponse.model.model_id).length).toBeGreaterThan(0);
});

test("errors are attached to their field by position, with translated reasons", async () => {
  const entries = [
    { position: 1, reasons: ["digit_or_symbol"], tokens: 6, max_tokens: 512 },
    { position: 2, reasons: ["exceeds_model_context"], tokens: 513, max_tokens: 512 },
  ];
  await renderApp({ "/pairs": [jsonResponse(422, errorBody("invalid_entries", { entries }))] });
  fill("c4sa", "x".repeat(511));
  fireEvent.click(submit());
  await screen.findByRole("alert");
  const a = screen.getByLabelText("Concepto A");
  const b = screen.getByLabelText("Concepto B");
  expect(a.getAttribute("aria-invalid")).toBe("true");
  expect(document.getElementById(a.getAttribute("aria-describedby")!)!.textContent).toContain("contiene números o símbolos");
  expect(document.getElementById(b.getAttribute("aria-describedby")!)!.textContent).toContain("513 de 512 tokens");
  expect(screen.queryByText("Fixed English text.")).toBeNull(); // the backend's English message is never shown
});

test("a second click while the analysis runs sends nothing", async () => {
  const pending = deferred(jsonResponse(200, pairResponse));
  const server = await renderApp({ "/pairs": [pending.reply] });
  fill("casa", "perro");
  fireEvent.click(submit());
  fireEvent.click(submit());
  fireEvent.submit(submit().closest("form")!);
  expect(submit()).toHaveProperty("disabled", true);
  expect(screen.getByLabelText("Concepto A")).toHaveProperty("readOnly", true);
  expect(screen.getAllByText("Analizando…").length).toBeGreaterThan(0);
  await act(async () => pending.release());
  await screen.findByRole("region", { name: "Resultado" });
  expect(server.calls.filter((c) => c.path === "/pairs")).toHaveLength(1);
});

test("analysis_busy waits for Retry-After before a manual retry, and never retries alone", async () => {
  const server = await renderApp({
    "/pairs": [jsonResponse(503, errorBody("analysis_busy"), { "Retry-After": "2" }), jsonResponse(200, pairResponse)],
  });
  vi.useFakeTimers({ shouldAdvanceTime: true });
  fill("casa", "perro");
  fireEvent.click(submit());
  const retry = await screen.findByRole("button", { name: "Reintentar en 2 s" });
  expect(retry).toHaveProperty("disabled", true);
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(screen.getByRole("button", { name: "Reintentar en 1 s" })).toHaveProperty("disabled", true);
  await act(async () => vi.advanceTimersByTimeAsync(1000));
  expect(server.calls.filter((c) => c.path === "/pairs")).toHaveLength(1); // nothing was resent automatically
  fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByRole("region", { name: "Resultado" });
  expect(server.calls.filter((c) => c.path === "/pairs")).toHaveLength(2);
});

test("editing after a result withdraws it", async () => {
  await renderApp({ "/pairs": [jsonResponse(200, pairResponse)] });
  fill("casa", "perro");
  fireEvent.click(submit());
  await screen.findByRole("region", { name: "Resultado" });
  fireEvent.change(screen.getByLabelText("Concepto B"), { target: { value: "gato" } });
  expect(screen.queryByRole("region", { name: "Resultado" })).toBeNull();
  expect(screen.getByText("Las entradas cambiaron: el resultado anterior se retiró.")).toBeTruthy();
});

test("network, timeout-like and HTTP errors look different; a network error re-checks the service once", async () => {
  const server = await renderApp({ "/pairs": [new TypeError("Failed to fetch"), jsonResponse(500, errorBody("internal_error"))] });
  fill("casa", "perro");
  fireEvent.click(submit());
  expect((await screen.findByRole("alert")).textContent).toContain("No se pudo conectar con el backend.");
  await waitFor(() => expect(server.calls.filter((c) => c.path === "/health")).toHaveLength(2));
  fireEvent.click(submit());
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Se produjo un error interno."));
  expect(screen.getByRole("alert").textContent).toContain("3f2b8c1e-6d4a-4e7f-9b0c-2a5d8e1f4c76"); // request ID in the details
});
