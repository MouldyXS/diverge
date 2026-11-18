import { ERROR_CODES, REASONS, type EntryIssue, type ErrorCode, type ErrorResponse, type Reason } from "./types";

/**
 * network: the request did not reach the backend (server stopped, wrong address).
 * http: the backend answered with its ErrorResponse contract.
 * timeout: no answer in time; for an analysis, the backend may still be processing it.
 * unexpected: an answer that does not follow the contract (not JSON, or another shape).
 */
export type ApiErrorKind = "network" | "http" | "timeout" | "unexpected";

export interface ApiErrorInit {
  kind: ApiErrorKind;
  status?: number | null;
  code?: ErrorCode | null;
  details?: Record<string, unknown>;
  requestId?: string | null;
  retryAfter?: number | null;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly code: ErrorCode | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;
  readonly retryAfter: number | null;

  constructor(init: ApiErrorInit) {
    // The message never carries the backend's text or the user's entries.
    super(`api_error:${init.kind}${init.code ? `:${init.code}` : ""}`);
    this.name = "ApiError";
    this.kind = init.kind;
    this.status = init.status ?? null;
    this.code = init.code ?? null;
    this.details = init.details ?? {};
    this.requestId = init.requestId ?? null;
    this.retryAfter = init.retryAfter ?? null;
  }
}

export function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError({ kind: "unexpected" });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

export function isErrorCode(value: unknown): value is ErrorCode {
  return typeof value === "string" && (ERROR_CODES as readonly string[]).includes(value);
}

export function isReason(value: unknown): value is Reason {
  return typeof value === "string" && (REASONS as readonly string[]).includes(value);
}

export function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    isRecord(value) &&
    isErrorCode(value.code) &&
    typeof value.message === "string" &&
    isRecord(value.details) &&
    (value.request_id === null || typeof value.request_id === "string")
  );
}

/** Seconds from a Retry-After header holding a delay in seconds; null otherwise (an HTTP date is not used here). */
export function parseRetryAfter(header: string | null): number | null {
  if (header === null || !/^\d+$/.test(header.trim())) {
    return null;
  }
  return Number(header.trim());
}

/** The rejected entries of an `invalid_entries` error; malformed items are ignored. */
export function entryIssues(error: ApiError): EntryIssue[] {
  const entries = error.details.entries;
  if (!Array.isArray(entries)) {
    return [];
  }
  return entries.filter(
    (item): item is EntryIssue =>
      isRecord(item) &&
      isCount(item.position) &&
      Array.isArray(item.reasons) &&
      item.reasons.every(isReason) &&
      (item.tokens === null || isCount(item.tokens)) &&
      (item.max_tokens === null || isCount(item.max_tokens)),
  );
}

export function tooManyWordsDetails(error: ApiError): { maxWords: number; receivedAtLeast: number } | null {
  const { max_words: maxWords, received_at_least: receivedAtLeast } = error.details;
  return isCount(maxWords) && isCount(receivedAtLeast) ? { maxWords, receivedAtLeast } : null;
}

export function unavailableState(error: ApiError): string | null {
  const state = error.details.state;
  return typeof state === "string" ? state : null;
}

export function maxBytes(error: ApiError): number | null {
  const value = error.details.max_bytes;
  return isCount(value) ? value : null;
}
