// The only module that talks HTTP. Components call these functions and never `fetch` directly.
import { ApiError, isErrorResponse, parseRetryAfter } from "./errors";
import type { HealthResponse, ModelResponse, PairRequest, PairResponse, ServiceStatus, SetRequest, SetResponse } from "./types";

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export function resolveBaseUrl(configured: string | undefined): string {
  const value = configured?.trim();
  return (value ? value : DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export const API_BASE_URL = resolveBaseUrl(import.meta.env.VITE_DIVERGE_API_BASE_URL);

/** Milliseconds. An expired analysis is not cancelled on the server: the backend may still be processing it. */
export const TIMEOUTS = { status: 10_000, analysis: 60_000 } as const;

interface RawResponse {
  status: number;
  ok: boolean;
  body: unknown;
  requestId: string | null;
  retryAfter: number | null;
}

const NOT_JSON = Symbol("not-json");

async function send(method: "GET" | "POST", path: string, payload: unknown, timeoutMs: number): Promise<RawResponse> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  try {
    // Only Content-Type is sent: it is the one request header the backend's CORS policy allows.
    const init: RequestInit = { method, signal: controller.signal };
    if (payload !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(payload);
    }
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, init);
    } catch {
      throw new ApiError({ kind: timedOut ? "timeout" : "network" });
    }
    let text: string;
    try {
      text = await response.text();
    } catch {
      throw new ApiError({ kind: timedOut ? "timeout" : "network", status: response.status });
    }
    let body: unknown = NOT_JSON;
    if (text !== "") {
      try {
        body = JSON.parse(text);
      } catch {
        body = NOT_JSON;
      }
    }
    return {
      status: response.status,
      ok: response.ok,
      body,
      requestId: response.headers.get("X-Request-ID"),
      retryAfter: parseRetryAfter(response.headers.get("Retry-After")),
    };
  } finally {
    clearTimeout(timer);
  }
}

function failure(raw: RawResponse): ApiError {
  if (isErrorResponse(raw.body)) {
    return new ApiError({
      kind: "http",
      status: raw.status,
      code: raw.body.code,
      details: raw.body.details,
      requestId: raw.body.request_id ?? raw.requestId,
      retryAfter: raw.retryAfter,
    });
  }
  return new ApiError({ kind: "unexpected", status: raw.status, requestId: raw.requestId });
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function call<T>(method: "GET" | "POST", path: string, payload: unknown, timeoutMs: number): Promise<T> {
  const raw = await send(method, path, payload, timeoutMs);
  if (!raw.ok) {
    throw failure(raw);
  }
  if (!isObject(raw.body)) {
    throw new ApiError({ kind: "unexpected", status: raw.status, requestId: raw.requestId });
  }
  return raw.body as T;
}

const STATUSES: readonly string[] = ["ready", "failed", "stopping"];

/** `GET /health`. A 503 that carries a HealthResponse is a valid answer about the service state, not an error. */
export async function getHealth(): Promise<HealthResponse> {
  const raw = await send("GET", "/health", undefined, TIMEOUTS.status);
  if ((raw.status === 200 || raw.status === 503) && isObject(raw.body) && STATUSES.includes(String(raw.body.status))) {
    return { status: raw.body.status as ServiceStatus };
  }
  throw raw.ok ? new ApiError({ kind: "unexpected", status: raw.status, requestId: raw.requestId }) : failure(raw);
}

export function getModel(): Promise<ModelResponse> {
  return call<ModelResponse>("GET", "/model", undefined, TIMEOUTS.status);
}

/** The words are sent exactly as typed: no trimming and no validation here (the engine validates). */
export function analyzePair(request: PairRequest): Promise<PairResponse> {
  return call<PairResponse>("POST", "/pairs", request, TIMEOUTS.analysis);
}

export function analyzeSet(request: SetRequest): Promise<SetResponse> {
  return call<SetResponse>("POST", "/sets", request, TIMEOUTS.analysis);
}
