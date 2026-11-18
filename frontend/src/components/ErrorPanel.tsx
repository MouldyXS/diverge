import { useEffect, useState } from "react";

import { type ApiError, maxBytes, tooManyWordsDetails, unavailableState } from "../api/errors";
import { copy } from "../copy";

function describe(error: ApiError): string {
  if (error.kind === "network") {
    return copy.errors.network;
  }
  if (error.kind === "timeout") {
    return copy.errors.timeout;
  }
  if (error.kind === "unexpected" || error.code === null) {
    return copy.errors.unexpected;
  }
  switch (error.code) {
    case "too_many_words": {
      const details = tooManyWordsDetails(error);
      return details ? copy.errors.tooManyWords(details.maxWords) : copy.errors.codes.too_many_words;
    }
    case "service_unavailable": {
      const state = unavailableState(error);
      const label = state === "failed" || state === "stopping" ? copy.errors.unavailableState[state] : "";
      return label ? copy.errors.unavailableWith(label) : copy.errors.codes.service_unavailable;
    }
    case "payload_too_large": {
      const bytes = maxBytes(error);
      return bytes === null ? copy.errors.codes.payload_too_large : `${copy.errors.codes.payload_too_large} ${copy.errors.maxBytes(bytes)}`;
    }
    case "invalid_entries":
      return `${copy.errors.codes.invalid_entries} ${copy.errors.seeEntries}`;
    default:
      return copy.errors.codes[error.code];
  }
}

function RetryAfter({ seconds, onRetry, disabled }: { seconds: number; onRetry: () => void; disabled: boolean }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    if (left <= 0) {
      return undefined;
    }
    const timer = setTimeout(() => setLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [left]);
  return (
    <button type="button" className="button button--secondary" onClick={onRetry} disabled={disabled || left > 0}>
      {left > 0 ? copy.errors.retryIn(left) : copy.errors.retry}
    </button>
  );
}

interface Props {
  error: ApiError;
  onRetry: () => void;
  onRecheck: () => void;
  retryDisabled: boolean;
}

/** One presentation per kind of failure: network, timeout, HTTP contract error, unexpected answer. */
export function ErrorPanel({ error, onRetry, onRecheck, retryDisabled }: Props) {
  const busy = error.code === "analysis_busy";
  const variant = error.kind === "timeout" ? "timeout" : busy ? "busy" : error.kind;
  return (
    <div className={`error-panel error-panel--${variant}`} role="alert">
      <h3 className="error-panel__title">{copy.errors.title}</h3>
      <p>{describe(error)}</p>
      <div className="actions">
        {busy && <RetryAfter seconds={error.retryAfter ?? 1} onRetry={onRetry} disabled={retryDisabled} />}
        {(error.kind === "network" || error.kind === "timeout" || error.code === "service_unavailable") && (
          <button type="button" className="button button--secondary" onClick={onRecheck}>
            {copy.errors.recheck}
          </button>
        )}
      </div>
      {(error.code !== null || error.status !== null || error.requestId !== null) && (
        <details>
          <summary>{copy.errors.technical}</summary>
          <dl className="kv">
            {error.code !== null && (
              <>
                <dt>{copy.errors.code}</dt>
                <dd>
                  <code>{error.code}</code>
                </dd>
              </>
            )}
            {error.status !== null && (
              <>
                <dt>{copy.errors.status}</dt>
                <dd className="num">{error.status}</dd>
              </>
            )}
            {error.requestId !== null && (
              <>
                <dt>{copy.errors.requestId}</dt>
                <dd>
                  <code>{error.requestId}</code>
                </dd>
              </>
            )}
          </dl>
        </details>
      )}
    </div>
  );
}
