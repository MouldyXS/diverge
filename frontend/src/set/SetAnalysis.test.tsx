import { act, fireEvent, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { P0_NOTICE } from "../copy";
import { errorBody, jsonResponse, modelResponse, setResponse } from "../test/fixtures";
import { deferred, renderApp } from "../test/render";

function openSet() {
  fireEvent.click(screen.getByRole("tab", { name: "Conjunto" }));
}

const rows = () => screen.getAllByRole("textbox", { name: /^Concepto \d+$/ });
const add = () => screen.getByRole("button", { name: "Añadir concepto" });
const submit = () => screen.getByRole("button", { name: "Analizar conjunto" });

function type(values: string[]) {
  values.forEach((value, k) => fireEvent.change(rows()[k]!, { target: { value } }));
}

test("the row limit comes from /model", async () => {
  await renderApp();
  openSet();
  expect(rows()).toHaveLength(3);
  expect(screen.getByText("Máximo de 5 entradas por conjunto.")).toBeTruthy();
  fireEvent.click(add());
  fireEvent.click(add());
  expect(rows()).toHaveLength(5);
  expect(add()).toHaveProperty("disabled", true);
});

test("without /model no row can be added and no limit is invented", async () => {
  await renderApp({ "/model": [new TypeError("Failed to fetch")] });
  openSet();
  expect(add()).toHaveProperty("disabled", true);
  expect(screen.getByText("El límite de entradas se conocerá al obtener los metadatos del modelo.")).toBeTruthy();
  expect(submit()).toHaveProperty("disabled", false); // analyzing is still possible; the backend applies its limit
});

test("every row is sent as typed, empty and repeated ones included", async () => {
  const server = await renderApp({ "/sets": [jsonResponse(200, setResponse)] });
  openSet();
  type(["Guerra ", "", "guerra"]);
  fireEvent.click(submit());
  await screen.findByRole("region", { name: "Resultado del conjunto" });
  expect(server.calls.find((c) => c.path === "/sets")!.body).toEqual({ words: ["Guerra ", "", "guerra"] });
});

test("pasting several lines fills the rows without trimming or splitting by spaces", async () => {
  await renderApp();
  openSet();
  fireEvent.click(screen.getByRole("button", { name: "Pegar varias líneas" }));
  fireEvent.change(screen.getByLabelText("Una palabra por línea"), { target: { value: "uno\r\n\r\ndos palabras \n" } });
  fireEvent.click(screen.getByRole("button", { name: "Reemplazar las filas" }));
  expect(rows().map((row) => (row as HTMLInputElement).value)).toEqual(["uno", "", "dos palabras "]);
});

test("shows the summary, extremes, matrix, pair table and the P0 notice", async () => {
  await renderApp({ "/sets": [jsonResponse(200, setResponse)] });
  openSet();
  type(["guerra", "paz", "noche"]);
  fireEvent.click(submit());
  const result = await screen.findByRole("region", { name: "Resultado del conjunto" });
  expect(within(result).getByText("Distancia media")).toBeTruthy();
  expect(within(result).getByText(/no mide creatividad/)).toBeTruthy();
  expect(within(result).getByText("0,2521").getAttribute("title")).toBe("0.2520843547469884"); // unscaled
  expect(within(result).getByText("Pareja más cercana")).toBeTruthy();
  expect(within(result).getByText("Pareja más distante")).toBeTruthy();
  const matrix = within(result).getByRole("table", { name: "Distancia coseno entre cada par de conceptos" });
  expect(within(matrix).getAllByText("no aplica")).toHaveLength(3);
  expect(within(matrix).getAllByText("0,1815")).toHaveLength(2); // both symmetric cells
  expect(within(result).getByText(P0_NOTICE[2])).toBeTruthy();
  const table = within(result).getByRole("region", { name: "Todas las parejas" });
  expect(within(table).getAllByRole("row")).toHaveLength(4);
});

test("the matrix has a single tab stop and is navigated with the arrow keys", async () => {
  await renderApp({ "/sets": [jsonResponse(200, setResponse)] });
  openSet();
  type(["guerra", "paz", "noche"]);
  fireEvent.click(submit());
  const result = await screen.findByRole("region", { name: "Resultado del conjunto" });
  const grid = within(result).getByRole("group", { name: "Distancia coseno entre cada par de conceptos" });
  expect(grid.tabIndex).toBe(0);
  expect(within(grid).queryAllByRole("button")).toHaveLength(0);
  expect(Array.from(grid.querySelectorAll("td")).every((cell) => cell.tabIndex < 0)).toBe(true);
  fireEvent.keyDown(grid, { key: "ArrowRight" });
  expect(within(result).getByText(/guerra — paz: distancia 0,1815 \(valor completo 0\.18148765432109876\)/)).toBeTruthy();
  fireEvent.keyDown(grid, { key: "ArrowRight" });
  expect(within(result).getByText(/guerra — noche: distancia 0,2988/)).toBeTruthy();
  fireEvent.keyDown(grid, { key: "ArrowLeft" });
  fireEvent.keyDown(grid, { key: "ArrowLeft" });
  expect(within(result).getByText("guerra — guerra: no aplica")).toBeTruthy();
});

test("sorting the pair table does not change the result", async () => {
  await renderApp({ "/sets": [jsonResponse(200, setResponse)] });
  openSet();
  type(["guerra", "paz", "noche"]);
  fireEvent.click(submit());
  const table = await screen.findByRole("region", { name: "Todas las parejas" });
  const distances = () => within(table).getAllByRole("row").slice(1).map((row) => row.lastElementChild!.textContent);
  expect(distances()).toEqual(["0,1815", "0,2988", "0,2760"]);
  fireEvent.click(within(table).getByRole("button", { name: /Distancia/ }));
  expect(distances()).toEqual(["0,1815", "0,2760", "0,2988"]);
  fireEvent.click(within(table).getByRole("button", { name: /Distancia/ }));
  expect(distances()).toEqual(["0,2988", "0,2760", "0,1815"]);
  expect(setResponse.pairs.map((pair) => pair.distance)).toEqual([0.18148765432109876, 0.2987654321098766, 0.2759999999999999]);
});

test("errors are shown on their rows by position", async () => {
  const entries = [
    { position: 2, reasons: ["empty"], tokens: 2, max_tokens: 512 },
    { position: 3, reasons: ["duplicate"], tokens: 8, max_tokens: 512 },
  ];
  await renderApp({ "/sets": [jsonResponse(422, errorBody("invalid_entries", { entries }))] });
  openSet();
  type(["guerra", "", "guerra"]);
  fireEvent.click(submit());
  await screen.findByRole("alert");
  const [first, second, third] = rows();
  expect(first!.getAttribute("aria-invalid")).toBe("false");
  expect(document.getElementById(second!.getAttribute("aria-describedby")!)!.textContent).toContain("está vacía");
  expect(document.getElementById(third!.getAttribute("aria-describedby")!)!.textContent).toContain("repite una entrada anterior");
});

test("too_many_words uses the backend's limit in the message", async () => {
  await renderApp({ "/sets": [jsonResponse(422, errorBody("too_many_words", { max_words: 5, received_at_least: 6 }))] });
  openSet();
  fireEvent.click(submit());
  expect((await screen.findByRole("alert")).textContent).toContain("Se superó el máximo de 5 entradas.");
});

test("an analysis in one mode disables both modes", async () => {
  const pending = deferred(jsonResponse(200, setResponse));
  await renderApp({ "/sets": [pending.reply] });
  openSet();
  type(["guerra", "paz", "noche"]);
  fireEvent.click(submit());
  expect(submit()).toHaveProperty("disabled", true);
  fireEvent.click(screen.getByRole("tab", { name: "Pareja" }));
  fireEvent.change(screen.getByLabelText("Concepto A"), { target: { value: "casa" } });
  fireEvent.change(screen.getByLabelText("Concepto B"), { target: { value: "perro" } });
  expect(screen.getByRole("button", { name: "Analizar pareja" })).toHaveProperty("disabled", true);
  await act(async () => pending.release());
  expect(screen.getByRole("button", { name: "Analizar pareja" })).toHaveProperty("disabled", false);
  expect(modelResponse.limits.max_words).toBe(5);
});
