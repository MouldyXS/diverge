import type { ApiError } from "../api/errors";
import type { SetResponse } from "../api/types";
import type { RequestStatus } from "../pair/pairReducer";

export interface Row {
  id: number; // stable React key; the position is the row's index + 1
  value: string;
}

export interface SetState {
  rows: Row[];
  nextId: number;
  status: RequestStatus;
  result: SetResponse | null;
  error: ApiError | null;
  withdrawn: boolean;
  pasteOpen: boolean;
  pasteText: string;
}

export type SetAction =
  | { type: "edit"; id: number; value: string }
  | { type: "add" }
  | { type: "remove"; id: number }
  | { type: "openPaste" }
  | { type: "pasteText"; value: string }
  | { type: "applyPaste" }
  | { type: "cancelPaste" }
  | { type: "submit" }
  | { type: "success"; result: SetResponse }
  | { type: "failure"; error: ApiError };

export const INITIAL_ROWS = 3;

export function initialSet(): SetState {
  return {
    rows: Array.from({ length: INITIAL_ROWS }, (_, id) => ({ id, value: "" })),
    nextId: INITIAL_ROWS,
    status: "idle",
    result: null,
    error: null,
    withdrawn: false,
    pasteOpen: false,
    pasteText: "",
  };
}

/**
 * Splits pasted text into entries by line breaks only (CRLF, LF or CR). Empty lines in the middle are kept and no
 * entry is trimmed; only the empty line created by a final line break is dropped. Spaces never split an entry, so
 * an entry with two words still reaches the engine and is reported as `multiple_words`.
 */
export function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\r|\n/);
  if (lines.length > 1 && lines[lines.length - 1] === "") {
    lines.pop();
  }
  return lines;
}

function changed(state: SetState, next: Partial<SetState>): SetState {
  const hadOutcome = state.result !== null || state.error !== null;
  return { ...state, ...next, result: null, error: null, status: "idle", withdrawn: hadOutcome || state.withdrawn };
}

export function setReducer(state: SetState, action: SetAction): SetState {
  if (state.status === "loading" && action.type !== "success" && action.type !== "failure") {
    return state; // nothing changes while an analysis of these rows runs
  }
  switch (action.type) {
    case "edit":
      return changed(state, { rows: state.rows.map((row) => (row.id === action.id ? { ...row, value: action.value } : row)) });
    case "add":
      return changed(state, { rows: [...state.rows, { id: state.nextId, value: "" }], nextId: state.nextId + 1 });
    case "remove":
      return changed(state, { rows: state.rows.filter((row) => row.id !== action.id) });
    case "openPaste":
      return { ...state, pasteOpen: true, pasteText: "" };
    case "pasteText":
      return { ...state, pasteText: action.value };
    case "cancelPaste":
      return { ...state, pasteOpen: false, pasteText: "" };
    case "applyPaste": {
      if (state.pasteText === "") {
        return { ...state, pasteOpen: false };
      }
      const lines = splitLines(state.pasteText);
      const rows = lines.map((value, k) => ({ id: state.nextId + k, value }));
      return changed(state, { rows, nextId: state.nextId + lines.length, pasteOpen: false, pasteText: "" });
    }
    case "submit":
      return { ...state, status: "loading", result: null, error: null, withdrawn: false };
    case "success":
      return { ...state, status: "success", result: action.result };
    case "failure":
      return { ...state, status: "error", error: action.error };
  }
}
