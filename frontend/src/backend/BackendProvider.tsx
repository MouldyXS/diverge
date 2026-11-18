import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from "react";

import { getHealth, getModel } from "../api/client";
import { ApiError, toApiError } from "../api/errors";
import type { HealthResponse, ModelResponse } from "../api/types";

/** checking: first request in flight; unreachable: no answer (network or timeout); unknown: an answer outside the contract. */
export type Connection = "checking" | "ready" | "failed" | "stopping" | "unreachable" | "unknown";

interface State {
  connection: Connection;
  model: ModelResponse | null;
  modelError: ApiError | null;
  checking: boolean;
  /** An analysis started from this browser tab is in flight (the backend still decides admission). */
  busy: boolean;
}

type Action =
  | { type: "check" }
  | { type: "checked"; health: HealthResponse | ApiError; model: ModelResponse | ApiError }
  | { type: "busy"; busy: boolean };

const initial: State = { connection: "checking", model: null, modelError: null, checking: true, busy: false };

function connectionOf(health: HealthResponse | ApiError): Connection {
  if (health instanceof ApiError) {
    return health.kind === "network" || health.kind === "timeout" ? "unreachable" : "unknown";
  }
  return health.status;
}

export function backendReducer(state: State, action: Action): State {
  switch (action.type) {
    case "check":
      return { ...state, checking: true };
    case "checked":
      return {
        ...state,
        checking: false,
        connection: connectionOf(action.health),
        // The limits are never guessed: without a successful /model answer there is no model and no limit.
        model: action.model instanceof ApiError ? null : action.model,
        modelError: action.model instanceof ApiError ? action.model : null,
      };
    case "busy":
      return { ...state, busy: action.busy };
  }
}

export interface Backend extends State {
  /** Query /health and /model again (manual button, or once after an analysis failed for a service reason). */
  refresh: () => void;
  /** Reserve the single local analysis slot; false if one is already running in this tab. */
  tryAcquire: () => boolean;
  release: () => void;
}

const BackendContext = createContext<Backend | null>(null);

async function settle<T>(promise: Promise<T>): Promise<T | ApiError> {
  try {
    return await promise;
  } catch (error) {
    return toApiError(error);
  }
}

export function BackendProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(backendReducer, initial);
  const checking = useRef(false);
  const started = useRef(false);
  const slot = useRef(false);

  const refresh = useCallback(() => {
    if (checking.current) {
      return;
    }
    checking.current = true;
    dispatch({ type: "check" });
    void Promise.all([settle(getHealth()), settle(getModel())]).then(([health, model]) => {
      checking.current = false;
      dispatch({ type: "checked", health, model });
    });
  }, []);

  useEffect(() => {
    if (!started.current) {
      started.current = true;
      refresh();
    }
  }, [refresh]);

  const tryAcquire = useCallback(() => {
    if (slot.current) {
      return false;
    }
    slot.current = true;
    dispatch({ type: "busy", busy: true });
    return true;
  }, []);

  const release = useCallback(() => {
    slot.current = false;
    dispatch({ type: "busy", busy: false });
  }, []);

  const value = useMemo(() => ({ ...state, refresh, tryAcquire, release }), [state, refresh, tryAcquire, release]);
  return <BackendContext.Provider value={value}>{children}</BackendContext.Provider>;
}

export function useBackend(): Backend {
  const backend = useContext(BackendContext);
  if (backend === null) {
    throw new Error("useBackend must be used inside BackendProvider");
  }
  return backend;
}

/** Errors after which the service state may have changed, so it is checked once again. */
export function needsRecheck(error: ApiError): boolean {
  return (
    error.kind === "network" ||
    error.kind === "timeout" ||
    error.code === "service_unavailable" ||
    error.code === "internal_error"
  );
}
