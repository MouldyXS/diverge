import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ApiError } from "../api/errors";
import { ErrorPanel } from "./ErrorPanel";

function show(error: ApiError) {
  const onRecheck = vi.fn();
  render(<ErrorPanel error={error} onRetry={vi.fn()} onRecheck={onRecheck} retryDisabled={false} />);
  return { panel: screen.getByRole("alert"), onRecheck };
}

test("a timeout says the result could not be confirmed and offers a status check, not a cancellation", () => {
  const { panel, onRecheck } = show(new ApiError({ kind: "timeout" }));
  expect(panel.className).toContain("error-panel--timeout");
  expect(panel.textContent).toContain("No se pudo confirmar el resultado");
  expect(panel.textContent).toContain("podría seguir procesando");
  expect(panel.textContent).not.toMatch(/cancel/i);
  fireEvent.click(screen.getByRole("button", { name: "Comprobar el estado" }));
  expect(onRecheck).toHaveBeenCalledTimes(1);
});

test("network, HTTP and unexpected answers have distinct presentations", () => {
  const network = show(new ApiError({ kind: "network" })).panel;
  expect(network.className).toContain("error-panel--network");
  expect(network.textContent).toContain("No se pudo conectar con el backend.");
});

test("an unexpected answer is not described with backend text", () => {
  const { panel } = show(new ApiError({ kind: "unexpected", status: 502 }));
  expect(panel.className).toContain("error-panel--unexpected");
  expect(panel.textContent).toContain("El servicio respondió de una forma inesperada.");
  expect(panel.textContent).toContain("502");
});

test("service_unavailable and payload_too_large use their details", () => {
  const unavailable = show(new ApiError({ kind: "http", status: 503, code: "service_unavailable", details: { state: "stopping" } })).panel;
  expect(unavailable.className).toContain("error-panel--http");
  expect(unavailable.textContent).toContain("El servicio no está disponible (cerrándose).");
});

test("payload_too_large shows the limit in bytes", () => {
  const { panel } = show(new ApiError({ kind: "http", status: 413, code: "payload_too_large", details: { max_bytes: 262144 } }));
  expect(panel.textContent).toContain("La solicitud supera el tamaño permitido. Límite: 262144 bytes.");
});
