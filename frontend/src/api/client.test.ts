import { describe, expect, test, vi } from "vitest";

import { errorBody, jsonResponse, modelResponse, pairResponse, requestId, setResponse } from "../test/fixtures";
import { API_BASE_URL, analyzePair, analyzeSet, getHealth, getModel, resolveBaseUrl, TIMEOUTS } from "./client";
import { ApiError, entryIssues, maxBytes, tooManyWordsDetails, unavailableState } from "./errors";

function stubFetch(...responses: (Response | Error)[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  const queue = [...responses];
  vi.stubGlobal("fetch", (url: string, init: RequestInit) => {
    calls.push({ url, init });
    const next = queue.shift();
    return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
  });
  return calls;
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("expected a rejection");
}

describe("base URL", () => {
  test("defaults to the local backend and drops trailing slashes", () => {
    expect(API_BASE_URL).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveBaseUrl(undefined)).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveBaseUrl("  ")).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveBaseUrl("http://127.0.0.1:9000/api/v1//")).toBe("http://127.0.0.1:9000/api/v1");
  });
});

describe("requests", () => {
  test("GET requests send no body and no extra header", async () => {
    const calls = stubFetch(jsonResponse(200, modelResponse));
    expect(await getModel()).toEqual(modelResponse);
    expect(calls).toHaveLength(1);
    expect(calls[0]!.url).toBe("http://127.0.0.1:8000/api/v1/model");
    expect(calls[0]!.init.method).toBe("GET");
    expect(calls[0]!.init.body).toBeUndefined();
    expect(calls[0]!.init.headers).toBeUndefined();
  });

  test("POST requests serialize the entries exactly as typed, with only Content-Type", async () => {
    const calls = stubFetch(jsonResponse(200, pairResponse), jsonResponse(200, setResponse));
    expect(await analyzePair({ word_a: " Casa ", word_b: "perro" })).toEqual(pairResponse);
    expect(await analyzeSet({ words: ["guerra", "", "dos palabras", "guerra"] })).toEqual(setResponse);
    expect(calls[0]!.url).toBe("http://127.0.0.1:8000/api/v1/pairs");
    expect(calls[0]!.init.method).toBe("POST");
    expect(calls[0]!.init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(calls[0]!.init.body))).toEqual({ word_a: " Casa ", word_b: "perro" });
    expect(calls[1]!.url).toBe("http://127.0.0.1:8000/api/v1/sets");
    expect(JSON.parse(String(calls[1]!.init.body))).toEqual({ words: ["guerra", "", "dos palabras", "guerra"] });
    expect(calls.every((c) => !c.url.includes("guerra") && !c.url.includes("Casa"))).toBe(true);
  });

  test("numbers are returned without rounding", async () => {
    stubFetch(jsonResponse(200, pairResponse));
    const result = await analyzePair({ word_a: "casa", word_b: "perro" });
    expect(result.distance).toBe(0.2568367083612715);
  });
});

describe("health", () => {
  test("200 and 503 with a HealthResponse are both valid states", async () => {
    stubFetch(jsonResponse(200, { status: "ready" }), jsonResponse(503, { status: "failed" }), jsonResponse(503, { status: "stopping" }));
    expect(await getHealth()).toEqual({ status: "ready" });
    expect(await getHealth()).toEqual({ status: "failed" });
    expect(await getHealth()).toEqual({ status: "stopping" });
  });

  test("a network failure is not a service state", async () => {
    stubFetch(new TypeError("Failed to fetch"));
    expect((await rejection(getHealth())).kind).toBe("network");
  });

  test("an unknown status is an unexpected response", async () => {
    stubFetch(jsonResponse(200, { status: "sleeping" }));
    expect((await rejection(getHealth())).kind).toBe("unexpected");
  });
});

describe("errors", () => {
  test("422 invalid_entries keeps code, details and request ID from the body", async () => {
    const entries = [{ position: 2, reasons: ["duplicate"], tokens: 12, max_tokens: 512 }];
    stubFetch(jsonResponse(422, errorBody("invalid_entries", { entries }), { "X-Request-ID": "other-header-id" }));
    const error = await rejection(analyzeSet({ words: ["a", "a"] }));
    expect([error.kind, error.status, error.code, error.requestId]).toEqual(["http", 422, "invalid_entries", requestId]);
    expect(entryIssues(error)).toEqual(entries);
    expect(error.message).not.toContain("Fixed English text");
  });

  test("the request ID falls back to the header when the body has none", async () => {
    stubFetch(jsonResponse(422, errorBody("too_few_words", {}, null), { "X-Request-ID": "header-id" }));
    expect((await rejection(analyzeSet({ words: ["a"] }))).requestId).toBe("header-id");
  });

  test("413, too_many_words and service_unavailable details", async () => {
    stubFetch(
      jsonResponse(413, errorBody("payload_too_large", { max_bytes: 262144 }), { Connection: "close" }),
      jsonResponse(422, errorBody("too_many_words", { max_words: 32, received_at_least: 33 })),
      jsonResponse(503, errorBody("service_unavailable", { state: "failed" })),
    );
    const large = await rejection(analyzeSet({ words: ["x"] }));
    expect([large.status, large.code, maxBytes(large)]).toEqual([413, "payload_too_large", 262144]);
    const many = await rejection(analyzeSet({ words: ["x"] }));
    expect(tooManyWordsDetails(many)).toEqual({ maxWords: 32, receivedAtLeast: 33 });
    const unavailable = await rejection(analyzePair({ word_a: "a", word_b: "b" }));
    expect([unavailable.status, unavailable.code, unavailableState(unavailable)]).toEqual([503, "service_unavailable", "failed"]);
  });

  test("analysis_busy keeps Retry-After", async () => {
    stubFetch(jsonResponse(503, errorBody("analysis_busy"), { "Retry-After": "1" }));
    const busy = await rejection(analyzePair({ word_a: "a", word_b: "b" }));
    expect([busy.code, busy.retryAfter]).toEqual(["analysis_busy", 1]);
  });

  test("a non-JSON or foreign answer is an unexpected response", async () => {
    stubFetch(jsonResponse(502, "Bad gateway"), jsonResponse(200, "not json"), jsonResponse(500, { detail: "x" }), jsonResponse(200, [1, 2]));
    for (let k = 0; k < 4; k += 1) {
      const error = await rejection(getModel());
      expect(error.kind).toBe("unexpected");
    }
  });

  test("a connection failure is a network error", async () => {
    stubFetch(new TypeError("Failed to fetch"));
    const error = await rejection(analyzePair({ word_a: "a", word_b: "b" }));
    expect([error.kind, error.status, error.code]).toEqual(["network", null, null]);
  });

  test("timeouts: 10 s for status requests, 60 s for analyses, without retrying", async () => {
    expect(TIMEOUTS).toEqual({ status: 10_000, analysis: 60_000 });
    vi.useFakeTimers();
    let calls = 0;
    vi.stubGlobal("fetch", (_url: string, init: RequestInit) => {
      calls += 1;
      return new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      });
    });
    const analysis = rejection(analyzeSet({ words: ["a", "b"] }));
    await vi.advanceTimersByTimeAsync(59_999);
    const status = rejection(getModel());
    await vi.advanceTimersByTimeAsync(1);
    expect((await analysis).kind).toBe("timeout");
    await vi.advanceTimersByTimeAsync(10_000);
    expect((await status).kind).toBe("timeout");
    expect(calls).toBe(2);
  });
});
