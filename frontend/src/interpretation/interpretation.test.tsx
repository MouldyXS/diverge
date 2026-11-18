import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { copy, P0_NOTICE } from "../copy";
import { formatDisplayedDifference, formatValue } from "../format";
import { PairResult } from "../pair/PairResult";
import { SetResults } from "../set/SetResults";
import { interpretationCases } from "../test/interpretationCases";
import { pairResponse, setResponse } from "../test/fixtures";
import type { SetResponse } from "../api/types";
import { describePair, describeSet, PAIR_NOTE, setNotes } from "./describe";

const byName = (name: string): SetResponse => interpretationCases.find((c) => c.name === name)!.response;
const text = (response: SetResponse) => describeSet(response).join(" ");

describe("sets: golden sentences", () => {
  test("five concepts and ten pairs, a unique minimum and maximum", () => {
    expect(describeSet(byName("five concepts, ten pairs"))).toEqual([
      "Se compararon 10 parejas entre 5 conceptos.",
      "La distancia media es 0,2680 (indicador experimental).",
      "Las distancias oscilan entre 0,0500 y 0,3600 (un rango de 0,3100).",
      "La pareja “uno – dos” presenta la menor distancia, mientras que “cuatro – cinco” presenta la mayor.",
      "Respecto a la media de este conjunto, 6 parejas tienen una distancia superior y 4 parejas tienen una distancia inferior.",
    ]);
  });

  test("exact ties at both extremes", () => {
    expect(describeSet(byName("exact ties at both extremes"))).toEqual([
      "Se compararon 6 parejas entre 4 conceptos.",
      "La distancia media es 0,2417 (indicador experimental).",
      "Las distancias oscilan entre 0,2000 y 0,3000 (un rango de 0,1000).",
      "Hay 3 parejas con la menor distancia al redondear a cuatro decimales (0,2000; son exactamente iguales): “sol – mar”, “sol – hoja” y “piedra – hoja”.",
      "Hay 2 parejas con la mayor distancia al redondear a cuatro decimales (0,3000; son exactamente iguales): “mar – piedra” y “sol – piedra”.",
      "Respecto a la media de este conjunto, 3 parejas tienen una distancia superior y 3 parejas tienen una distancia inferior.",
    ]);
  });

  test("a tie at the shown value that is not an exact tie is said so", () => {
    const sentences = describeSet(byName("tie at the shown value but not exact"));
    expect(sentences[3]).toBe(
      "Hay 2 parejas con la menor distancia al redondear a cuatro decimales (0,1815; no son exactamente iguales): “sol – piedra” y “sol – mar”.",
    );
  });

  test("two concepts have one pair and no internal comparison", () => {
    expect(describeSet(byName("two concepts"))).toEqual([
      "Se comparó 1 pareja entre 2 conceptos.",
      "La distancia media es 0,1800 (indicador experimental).",
      "Con dos conceptos solo hay una pareja, de modo que la media, la mínima y la máxima coinciden (0,1800) y no hay comparación interna posible.",
    ]);
  });

  test("all distances equal: exactly, and only at four decimals", () => {
    expect(describeSet(byName("all exactly equal")).slice(2)).toEqual([
      "Todas las parejas tienen la misma distancia (0,2500) al redondear a cuatro decimales; son exactamente iguales.",
    ]);
    expect(describeSet(byName("all equal at four decimals")).slice(2)).toEqual([
      "Todas las parejas tienen la misma distancia (0,2500) al redondear a cuatro decimales; no son exactamente iguales.",
    ]);
  });

  test("a long tie lists five pairs and says how many more", () => {
    const sentence = describeSet(byName("more ties than are listed")).find((s) => s.startsWith("Hay "))!;
    expect(sentence).toBe(
      "Hay 8 parejas con la menor distancia al redondear a cuatro decimales (0,2000; son exactamente iguales): “a – b”, “a – c”, “a – d”, “a – e”, “a – f” y 3 más.",
    );
    expect(sentence.split("“").length - 1).toBe(5);
  });

  test("a pair equal to the mean at four decimals is counted apart", () => {
    expect(describeSet(byName("one pair equal to the mean")).at(-1)).toBe(
      "Respecto a la media de este conjunto, 1 pareja tiene una distancia superior, 1 pareja tiene una distancia inferior y 1 pareja coincide con ella al redondear a cuatro decimales.",
    );
  });

  test("singular and plural", () => {
    expect(copy.interpretation.set.compared(1, 2)).toBe("Se comparó 1 pareja entre 2 conceptos.");
    expect(copy.interpretation.set.compared(3, 3)).toBe("Se compararon 3 parejas entre 3 conceptos.");
    expect(copy.interpretation.set.relative(1, 0, 0)).toBe("Respecto a la media de este conjunto, 1 pareja tiene una distancia superior.");
    expect(copy.interpretation.set.relative(2, 3, 0)).toContain("2 parejas tienen una distancia superior y 3 parejas tienen");
    expect(copy.interpretation.set.relative(0, 0, 4)).toContain("4 parejas coinciden con ella");
  });
});

describe("numbers in the sentences correspond to the data", () => {
  test.each(interpretationCases.map((c) => [c.name, c.response] as const))("%s", (_name, response) => {
    const it = response.interpretation;
    const allowed = new Set([
      ...response.pairs.map((p) => formatValue(p.distance)),
      formatValue(response.mean_distance),
      formatValue(it.min_distance),
      formatValue(it.max_distance),
      formatDisplayedDifference(it.max_distance, it.min_distance),
    ]);
    const decimals = text(response).match(/\d+,\d{4}/g) ?? [];
    expect(decimals.length).toBeGreaterThan(0);
    for (const value of decimals) {
      expect(allowed.has(value), value).toBe(true);
    }
    expect(text(response)).toContain(`${response.n_pairs === 1 ? "Se comparó" : "Se compararon"} ${response.n_pairs} `);
    expect(text(response)).toContain(formatValue(response.mean_distance));
    // the counts that are spoken add up to the pairs
    if (!it.flags.includes("single_pair") && !it.flags.includes("all_equal_at_precision")) {
      expect(it.n_above_mean + it.n_below_mean + it.n_at_mean).toBe(response.n_pairs);
    }
  });

  test.each(interpretationCases.map((c) => [c.name, c.response] as const))("%s: the pairs named are the ones the API points to", (_n, response) => {
    const it = response.interpretation;
    const sentences = describeSet(response).join(" ");
    const first = (ref: { i: number; j: number }) => `“${response.words[ref.i]} – ${response.words[ref.j]}”`;
    if (!it.flags.includes("single_pair") && !it.flags.includes("all_equal_at_precision")) {
      expect(sentences).toContain(first(it.min_pairs[0]!));
      expect(sentences).toContain(first(it.max_pairs[0]!));
    }
    // the first listed extremes are the ones the interface already shows as closest / most distant
    expect([it.min_pairs[0]!.i, it.min_pairs[0]!.j]).toEqual([response.closest.i, response.closest.j]);
    expect([it.max_pairs[0]!.i, it.max_pairs[0]!.j]).toEqual([response.most_distant.i, response.most_distant.j]);
  });
});

describe("the range is consistent with the extremes the user sees", () => {
  const decimal = (text: string) => Math.round(Number(text.replace(",", ".")) * 10_000);

  test("the Granite case that exposed it: 0,3495 - 0,1815 = 0,1680 (the exact range rounds to 0,1679)", () => {
    const min = 0.1815446146280899;
    const max = 0.3494572716151898;
    expect(formatValue(min)).toBe("0,1815");
    expect(formatValue(max)).toBe("0,3495");
    expect(formatValue(max - min)).toBe("0,1679"); // what showing the exact range would have said
    expect(formatDisplayedDifference(max, min)).toBe("0,1680");
  });

  test("the sentence shows a range equal to the difference of the extremes it shows", () => {
    const response = structuredClone(byName("five concepts, ten pairs"));
    response.interpretation.min_distance = 0.1815446146280899;
    response.interpretation.max_distance = 0.3494572716151898;
    response.interpretation.range = response.interpretation.max_distance - response.interpretation.min_distance;
    const sentence = describeSet(response).find((line) => line.startsWith("Las distancias oscilan"))!;
    expect(sentence).toBe("Las distancias oscilan entre 0,1815 y 0,3495 (un rango de 0,1680).");
    expect(response.interpretation.range).toBeCloseTo(0.1679126569870999, 15); // the exact range is kept, unchanged
  });

  test("for any pair of values, shown maximum minus shown minimum equals the shown range", () => {
    let state = 12345;
    const random = () => ((state = (state * 1103515245 + 12345) % 2147483648) / 2147483648);
    for (let k = 0; k < 20000; k += 1) {
      const a = random() * 0.5;
      const b = random() * 0.5;
      const [low, high] = a <= b ? [a, b] : [b, a];
      const shown = formatDisplayedDifference(high, low);
      expect(decimal(shown), `${low} ${high}`).toBe(decimal(formatValue(high)) - decimal(formatValue(low)));
    }
  });

  test("equal at four decimals gives a range of 0,0000, and negative float noise does not break it", () => {
    expect(formatDisplayedDifference(0.18151, 0.18149)).toBe("0,0000");
    expect(formatDisplayedDifference(0.2, -2.2e-16)).toBe("0,2000");
    expect(formatDisplayedDifference(1e-17, -1e-17)).toBe("0,0000");
  });

  test.each(interpretationCases.map((c) => [c.name, c.response] as const))("%s: extremes and range in the sentence subtract correctly", (_name, response) => {
    const sentence = describeSet(response).find((line) => line.startsWith("Las distancias oscilan"));
    if (!sentence) return; // single pair and all-equal sets have no range sentence
    const [min, max, range] = sentence.match(/\d+,\d{4}/g)!;
    expect(decimal(max!) - decimal(min!)).toBe(decimal(range!));
  });
});

describe("pairs", () => {
  test("two paragraphs: the values, and what they are", () => {
    expect(describePair(pairResponse)).toEqual([
      "“casa” y “perro”: similitud 0,7432 y distancia 0,2568.",
      "La similitud corresponde al coseno del ángulo entre las representaciones numéricas de ambos conceptos; la distancia se calcula como 1 − similitud.",
    ]);
  });

  test("no percentage of the theoretical range and no classification", () => {
    const all = [...describePair(pairResponse), PAIR_NOTE].join(" ");
    expect(all).not.toMatch(/%|rango te[oó]rico|equivale/i);
    expect(PAIR_NOTE).toContain("no dispone de una distribución de referencia");
  });
});

describe("methodological warnings", () => {
  test("they are separate from the sentences and come from codes", () => {
    const notes = setNotes(setResponse.interpretation.notes);
    expect(notes).toEqual([
      "Las comparaciones con la media son relativas a este conjunto y no clasifican las parejas de forma general.",
      "Diverge no dispone de una distribución de referencia con la que clasificar una distancia como alta o baja.",
      "La distancia media es un indicador experimental y no una medida validada.",
    ]);
    for (const note of notes) expect(text(setResponse)).not.toContain(note);
  });

  test("no general claim about compressed distances", () => {
    const everything = [...Object.values(copy.interpretation.notes), PAIR_NOTE, ...interpretationCases.flatMap((c) => describeSet(c.response))].join(" ");
    expect(everything).not.toMatch(/compr[ií]mid|estrech|tramo/i);
  });
});

describe("no unjustified claims", () => {
  const FORBIDDEN =
    /creativ|intelig|original|divergen|percentil|poblaci|pensamiento|personalidad|sin relaci|no tienen relaci|relacionad|\bmuy\b|\bpoco\b|\bmucho\b|lejan|\btu\b|\btus\b|\busted|promedio|superior al/i;

  const everything = () => [
    ...interpretationCases.flatMap((c) => describeSet(c.response)),
    ...describeSet(setResponse),
    ...describePair(pairResponse),
    ...Object.values(copy.interpretation.notes),
    PAIR_NOTE,
    copy.interpretation.heading,
    copy.interpretation.howToRead,
  ];

  test("sentences and warnings contain none of the forbidden expressions", () => {
    for (const sentence of everything()) {
      expect(sentence, sentence).not.toMatch(FORBIDDEN);
    }
  });

  test("the sweep catches what it should", () => {
    for (const bad of ["tu creatividad es alta", "pensamiento divergente", "estos conceptos no tienen relación", "una asociación original", "percentil 90", "muy cercanas"]) {
      expect(bad).toMatch(FORBIDDEN);
    }
  });

  test("comparisons are only relative: superior, inferior, mayor, menor", () => {
    const relative = describeSet(byName("five concepts, ten pairs")).join(" ");
    expect(relative).toMatch(/superior/);
    expect(relative).toMatch(/inferior/);
    expect(relative).toMatch(/menor/);
    expect(relative).toMatch(/mayor/);
  });
});

describe("components next to the P0 notice", () => {
  test("a set result shows the reading, keeps the matrix, the table and the P0 notice", () => {
    render(<SetResults result={setResponse} />);
    const reading = screen.getByRole("region", { name: "Lectura descriptiva" });
    expect(within(reading).getByText(/Se compararon 3 parejas entre 3 conceptos\./)).toBeTruthy();
    expect(within(reading).getByText("Cómo leerlo")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Matriz de distancias" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Todas las parejas" })).toBeTruthy();
    expect(screen.getByText("Distancia media")).toBeTruthy();
    expect(screen.getByText("Pareja más cercana")).toBeTruthy();
    for (const paragraph of P0_NOTICE) expect(screen.getByText(paragraph)).toBeTruthy(); // unchanged, verbatim
    expect(reading.closest(".notice")).toBeNull(); // the reading is not inside the P0 notice, nor the notice inside it
    expect(reading.querySelector(".notice")).toBeNull();
  });

  test("a pair result shows the reading and the P0 notice, in different blocks", () => {
    render(<PairResult result={pairResponse} />);
    const reading = screen.getByRole("region", { name: "Lectura descriptiva" });
    expect(within(reading).getByText("“casa” y “perro”: similitud 0,7432 y distancia 0,2568.")).toBeTruthy();
    for (const paragraph of P0_NOTICE) expect(screen.getByText(paragraph)).toBeTruthy();
    expect(reading.contains(screen.getByText(P0_NOTICE[0]))).toBe(false);
  });

  test("the reading coexists with any wording of the notice", () => {
    // The sentences and warnings do not mention the notice or its vocabulary ("el índice"), so a different wording cannot clash.
    const everything = [...describeSet(setResponse), ...describePair(pairResponse), ...Object.values(copy.interpretation.notes), PAIR_NOTE].join(" ");
    expect(everything).not.toMatch(/índice|P0|solo revisa el formato/i);
  });
});

describe("the four-decimal rule agrees with the backend", () => {
  // The same table as backend/tests/test_interpretation.py (GOLDEN): what the interface shows for each value.
  const GOLDEN: [string, string][] = [
    ["0.00145", "0.0015"], ["0.00565", "0.0057"], ["0.00635", "0.0064"], ["0.00705", "0.0071"], ["0.00005", "0.0001"],
    ["0.00015", "0.0002"], ["0.00025", "0.0003"], ["0.18145", "0.1815"], ["0.18155", "0.1816"], ["0.18149", "0.1815"],
    ["0.18151", "0.1815"], ["0.18160", "0.1816"], ["0.30005", "0.3001"], ["0.34995", "0.3500"], ["0.34994999999999", "0.3499"],
    ["0.2", "0.2000"], ["0.2000000001", "0.2000"], ["0.19999999999", "0.2000"], ["0.12345", "0.1235"], ["0.12355", "0.1236"],
    ["0.99995", "1.0000"], ["1.00005", "1.0001"], ["1.5", "1.5000"], ["2", "2.0000"], ["0", "0.0000"], ["1e-05", "0.0000"],
    ["4.9999e-05", "0.0000"], ["5e-05", "0.0001"], ["0.00014999", "0.0001"], ["0.000149999999", "0.0001"],
    ["0.18148765432109876", "0.1815"], ["0.2987654321098766", "0.2988"],
  ];

  test.each(GOLDEN)("%s is shown as %s", (value, shown) => {
    expect(formatValue(Number(value)).replace(",", ".")).toBe(shown);
  });
});
