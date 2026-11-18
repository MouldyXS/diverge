import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test } from "vitest";

import { jsonResponse, modelResponse } from "../test/fixtures";
import { fakeServer } from "../test/server";
import { BackendProvider } from "./BackendProvider";
import { BackendStatus } from "./BackendStatus";
import { ModelPanel } from "./ModelPanel";

function renderStatus() {
  return render(
    <BackendProvider>
      <BackendStatus />
      <ModelPanel />
    </BackendProvider>,
  );
}

test("starts as connecting, then shows the ready state and the model from /model", async () => {
  const server = fakeServer({ "/health": [jsonResponse(200, { status: "ready" })], "/model": [jsonResponse(200, modelResponse)] });
  renderStatus();
  expect(screen.getByRole("status").textContent).toContain("Conectando");
  await screen.findByText("Disponible");
  expect(screen.getAllByText(modelResponse.model_id).length).toBeGreaterThan(0);
  expect(screen.getByText("512")).toBeTruthy(); // max_input_tokens from /model
  expect(screen.getByText("5")).toBeTruthy(); // max_words from /model
  expect(screen.getByText(/no un hash de los pesos/)).toBeTruthy();
  expect(server.calls.map((c) => c.path).sort()).toEqual(["/health", "/model"]); // queried once, in parallel
});

test.each([
  ["failed", "Servicio con fallo"],
  ["stopping", "Servicio cerrándose"],
])("a 503 with a HealthResponse (%s) is a service state, not a network failure", async (status, label) => {
  fakeServer({ "/health": [jsonResponse(503, { status })], "/model": [jsonResponse(200, modelResponse)] });
  renderStatus();
  await screen.findByText(label);
  expect(screen.queryByText("Backend inaccesible")).toBeNull();
});

test("a network failure shows the backend as unreachable with its address", async () => {
  fakeServer({ "/health": [new TypeError("Failed to fetch")], "/model": [new TypeError("Failed to fetch")] });
  renderStatus();
  await screen.findByText("Backend inaccesible");
  expect(screen.getByText(/127\.0\.0\.1:8000\/api\/v1/)).toBeTruthy();
});

test("ready without metadata says so and invents no limit", async () => {
  fakeServer({
    "/health": [jsonResponse(200, { status: "ready" })],
    "/model": [jsonResponse(500, { request_id: null, code: "internal_error", message: "x", details: {} })],
  });
  renderStatus();
  await screen.findByText(/Metadatos no disponibles/);
  expect(screen.queryByText("32")).toBeNull();
});

test("the manual button checks again; there is no polling", async () => {
  const server = fakeServer({
    "/health": [new TypeError("Failed to fetch"), jsonResponse(200, { status: "ready" })],
    "/model": [new TypeError("Failed to fetch"), jsonResponse(200, modelResponse)],
  });
  renderStatus();
  await screen.findByText("Backend inaccesible");
  expect(server.calls).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "Comprobar de nuevo" }));
  await screen.findByText("Disponible");
  await waitFor(() => expect(server.calls).toHaveLength(4));
});

test("a null snapshot is shown as not reported, never replaced by the declared revision", async () => {
  fakeServer({
    "/health": [jsonResponse(200, { status: "ready" })],
    "/model": [jsonResponse(200, { ...modelResponse, snapshot_revision: null, pooling_mode: null })],
  });
  renderStatus();
  await screen.findByText("Disponible");
  expect(screen.getAllByText("no informado").length).toBe(2);
  expect(screen.getAllByText(modelResponse.declared_revision)).toHaveLength(1);
});
