import { API_BASE_URL } from "../api/client";
import { copy } from "../copy";
import { useBackend, type Connection } from "./BackendProvider";

const LABELS: Record<Connection, string> = {
  checking: copy.backend.checking,
  ready: copy.backend.ready,
  failed: copy.backend.failed,
  stopping: copy.backend.stopping,
  unreachable: copy.backend.unreachable,
  unknown: copy.backend.unknown,
};

function hint(connection: Connection): string | null {
  switch (connection) {
    case "unreachable":
      return copy.backend.unreachableHint(API_BASE_URL);
    case "failed":
      return copy.backend.failedHint;
    case "stopping":
      return copy.backend.stoppingHint;
    default:
      return null;
  }
}

export function BackendStatus() {
  const { connection, model, checking, refresh } = useBackend();
  const message = hint(connection);
  const metadataMissing = connection === "ready" && model === null && !checking;
  return (
    <section className="header__status" aria-label={copy.backend.regionLabel}>
      <p className={`status status--${connection}`} role="status" aria-live="polite" aria-busy={checking}>
        <span className="status__dot" aria-hidden="true" />
        <span>{checking && connection !== "checking" ? copy.backend.rechecking : LABELS[connection]}</span>
      </p>
      {message && <p className="hint">{message}</p>}
      {metadataMissing && (
        <p className="hint">
          <strong>{copy.backend.metadataMissing}.</strong> {copy.backend.metadataMissingHint}
        </p>
      )}
      <button type="button" className="button button--secondary button--small" onClick={refresh} disabled={checking}>
        {copy.backend.recheck}
      </button>
    </section>
  );
}
