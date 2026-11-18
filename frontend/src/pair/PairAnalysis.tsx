import { useReducer, type FormEvent } from "react";

import { analyzePair } from "../api/client";
import { entryIssues, toApiError } from "../api/errors";
import { needsRecheck, useBackend } from "../backend/BackendProvider";
import { EntryErrors, hasIssue } from "../components/EntryErrors";
import { ErrorPanel } from "../components/ErrorPanel";
import { copy } from "../copy";
import { initialPair, pairReducer } from "./pairReducer";
import { PairResult } from "./PairResult";

const FIELDS = [
  { field: "a", position: 1, id: "pair-a", label: copy.pair.labelA },
  { field: "b", position: 2, id: "pair-b", label: copy.pair.labelB },
] as const;

export function PairAnalysis() {
  const backend = useBackend();
  const [state, dispatch] = useReducer(pairReducer, initialPair);
  const loading = state.status === "loading";
  const issues = state.error ? entryIssues(state.error) : [];
  const canSubmit = state.a !== "" && state.b !== "" && !backend.busy;

  async function run() {
    if (!canSubmit || !backend.tryAcquire()) {
      return;
    }
    dispatch({ type: "submit" });
    try {
      // Sent exactly as typed: no trimming, no validation (the engine applies P0 and the token limit).
      const result = await analyzePair({ word_a: state.a, word_b: state.b });
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
    <div className="split">
      <form className="card" onSubmit={onSubmit} aria-busy={loading} noValidate>
        <h2>{copy.pair.heading}</h2>
        <p className="muted">{copy.pair.intro}</p>
        {FIELDS.map(({ field, position, id, label }) => {
          const invalid = hasIssue(issues, position);
          return (
            <div className="field" key={field}>
              <label htmlFor={id}>{label}</label>
              <input
                id={id}
                type="text"
                autoComplete="off"
                spellCheck={false}
                value={state[field]}
                readOnly={loading}
                aria-invalid={invalid}
                aria-describedby={invalid ? `${id}-errors` : undefined}
                onChange={(event) => dispatch({ type: "edit", field, value: event.target.value })}
              />
              <EntryErrors id={`${id}-errors`} issues={issues} position={position} />
            </div>
          );
        })}
        <button type="submit" className="button" disabled={!canSubmit}>
          {copy.pair.submit}
        </button>
        <p className="muted" role="status" aria-live="polite">
          {loading ? copy.status.analyzing : state.withdrawn ? copy.status.stale : ""}
        </p>
      </form>
      <div aria-live="polite">
        {state.error && (
          <ErrorPanel error={state.error} onRetry={() => void run()} onRecheck={backend.refresh} retryDisabled={!canSubmit} />
        )}
        {state.result && <PairResult result={state.result} />}
      </div>
    </div>
  );
}
