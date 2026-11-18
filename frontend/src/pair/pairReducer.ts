import type { ApiError } from "../api/errors";
import type { PairResponse } from "../api/types";

export type RequestStatus = "idle" | "loading" | "success" | "error";

export interface PairState {
  a: string;
  b: string;
  status: RequestStatus;
  result: PairResponse | null;
  error: ApiError | null;
  /** A result or error was withdrawn because the entries changed after it. */
  withdrawn: boolean;
}

export type PairAction =
  | { type: "edit"; field: "a" | "b"; value: string }
  | { type: "submit" }
  | { type: "success"; result: PairResponse }
  | { type: "failure"; error: ApiError };

export const initialPair: PairState = { a: "", b: "", status: "idle", result: null, error: null, withdrawn: false };

export function pairReducer(state: PairState, action: PairAction): PairState {
  switch (action.type) {
    case "edit": {
      if (state.status === "loading") {
        return state; // the entries are read-only while their analysis runs
      }
      const hadOutcome = state.result !== null || state.error !== null;
      // A result never stays next to entries it does not belong to.
      return { ...state, [action.field]: action.value, result: null, error: null, status: "idle", withdrawn: hadOutcome || state.withdrawn };
    }
    case "submit":
      return { ...state, status: "loading", result: null, error: null, withdrawn: false };
    case "success":
      return { ...state, status: "success", result: action.result };
    case "failure":
      return { ...state, status: "error", error: action.error };
  }
}
