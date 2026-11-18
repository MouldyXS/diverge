import { useReducer, type FormEvent } from "react";

import { analyzeSet } from "../api/client";
import { entryIssues, toApiError } from "../api/errors";
import { needsRecheck, useBackend } from "../backend/BackendProvider";
import { EntryErrors, hasIssue } from "../components/EntryErrors";
import { ErrorPanel } from "../components/ErrorPanel";
import { copy } from "../copy";
import { SetResults } from "./SetResults";
import { initialSet, setReducer } from "./setReducer";

export function SetAnalysis() {
  const backend = useBackend();
  const [state, dispatch] = useReducer(setReducer, undefined, initialSet);
  const loading = state.status === "loading";
  const issues = state.error ? entryIssues(state.error) : [];
  // The limit comes only from /model; without it no row can be added (no value is guessed here).
  const maxWords = backend.model?.limits.max_words ?? null;
  const canAdd = !loading && maxWords !== null && state.rows.length < maxWords;
  const canSubmit = state.rows.length > 0 && !backend.busy;

  async function run() {
    if (!canSubmit || !backend.tryAcquire()) {
      return;
    }
    dispatch({ type: "submit" });
    try {
      // Every row is sent as typed, empty or repeated ones included: the engine validates them.
      const result = await analyzeSet({ words: state.rows.map((row) => row.value) });
      dispatch({ type: "success", result });
    } catch (caught) {
      const error = toApiError(caught);
      dispatch({ type: "failure", error });
      if (needsRecheck(error)) {
        backend.refresh();
      }
    } finally {
      backend.release();
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void run();
  }

  return (
    <div className="page-section">
      <form className="card" onSubmit={onSubmit} aria-busy={loading} noValidate>
        <h2>{copy.set.heading}</h2>
        <p className="muted">{copy.set.intro}</p>
        <p className="muted">
          {maxWords === null
            ? copy.set.limitUnknown
            : state.rows.length > maxWords
              ? copy.set.overLimit(state.rows.length, maxWords)
              : copy.set.limit(maxWords)}
        </p>
        {state.rows.map((row, index) => {
          const position = index + 1;
          const id = `set-entry-${row.id}`;
          const invalid = hasIssue(issues, position);
          return (
            <div className="row" key={row.id}>
              <span className="row__position num" aria-hidden="true">
                {position}
              </span>
              <input
                id={id}
                type="text"
                autoComplete="off"
                spellCheck={false}
                aria-label={copy.set.entry(position)}
                value={row.value}
                readOnly={loading}
                aria-invalid={invalid}
                aria-describedby={invalid ? `${id}-errors` : undefined}
                onChange={(event) => dispatch({ type: "edit", id: row.id, value: event.target.value })}
              />
              <button
                type="button"
                className="button button--secondary button--small"
                aria-label={copy.set.remove(position)}
                disabled={loading}
                onClick={() => dispatch({ type: "remove", id: row.id })}
              >
                {copy.set.removeShort}
              </button>
              <div className="row__errors">
                <EntryErrors id={`${id}-errors`} issues={issues} position={position} />
              </div>
            </div>
          );
        })}
        <div className="actions">
          <button type="button" className="button button--secondary" onClick={() => dispatch({ type: "add" })} disabled={!canAdd}>
            {copy.set.add}
          </button>
          <button type="button" className="button button--secondary" onClick={() => dispatch({ type: "openPaste" })} disabled={loading}>
            {copy.set.paste}
          </button>
        </div>
        {state.pasteOpen && (
          <div className="paste">
            <label htmlFor="set-paste">{copy.set.pasteLabel}</label>
            <textarea
              id="set-paste"
              rows={6}
              value={state.pasteText}
              onChange={(event) => dispatch({ type: "pasteText", value: event.target.value })}
            />
            <div className="actions">
              <button type="button" className="button button--secondary" onClick={() => dispatch({ type: "applyPaste" })}>
                {copy.set.pasteApply}
              </button>
              <button type="button" className="button button--secondary" onClick={() => dispatch({ type: "cancelPaste" })}>
                {copy.set.pasteCancel}
              </button>
            </div>
          </div>
        )}
        <button type="submit" className="button" disabled={!canSubmit}>
          {copy.set.submit}
        </button>
        <p className="muted" role="status" aria-live="polite">
          {loading ? copy.status.analyzing : state.withdrawn ? copy.status.stale : ""}
        </p>
      </form>
      <div aria-live="polite">
        {state.error && (
          <ErrorPanel error={state.error} onRetry={() => void run()} onRecheck={backend.refresh} retryDisabled={!canSubmit} />
        )}
        {state.result && <SetResults result={state.result} />}
      </div>
    </div>
  );
}
