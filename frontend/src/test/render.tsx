import { render, screen } from "@testing-library/react";

import { App } from "../App";
import { BackendProvider } from "../backend/BackendProvider";
import { jsonResponse, modelResponse } from "./fixtures";
import { fakeServer, type Reply } from "./server";

/** Renders the whole application against a routed fetch stub; /health and /model answer by default. */
export async function renderApp(routes: Record<string, Reply[]> = {}) {
  const server = fakeServer({
    "/health": [jsonResponse(200, { status: "ready" })],
    "/model": [jsonResponse(200, modelResponse)],
    ...routes,
  });
  render(
    <BackendProvider>
      <App />
    </BackendProvider>,
  );
  await screen.findByText(/^(Disponible|Backend inaccesible|Servicio con fallo|Servicio cerrándose|Estado desconocido)$/);
  return server;
}

/** A reply that waits until `release()` is called. */
export function deferred(response: Response) {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { reply: async () => (await gate, response), release: () => release() };
}
