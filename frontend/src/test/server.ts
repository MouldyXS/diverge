// A fetch stub routed by path, for component tests. Each route returns its responses in order (the last one repeats).
import { vi } from "vitest";

import { jsonResponse } from "./fixtures";

export type Reply = Response | Error | (() => Response | Error | Promise<Response>);

export interface FakeServer {
  calls: { path: string; method: string; body: unknown }[];
  route: (path: string, ...replies: Reply[]) => void;
}

export function fakeServer(routes: Record<string, Reply[]> = {}): FakeServer {
  const table = new Map<string, Reply[]>(Object.entries(routes));
  const calls: FakeServer["calls"] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const path = new URL(url).pathname.replace("/api/v1", "");
    calls.push({ path, method: init.method ?? "GET", body: init.body ? JSON.parse(String(init.body)) : undefined });
    const replies = table.get(path);
    if (!replies || replies.length === 0) {
      return jsonResponse(404, { request_id: null, code: "not_found", message: "Not found.", details: {} });
    }
    const reply = replies.length > 1 ? replies.shift()! : replies[0]!;
    const value = typeof reply === "function" ? await reply() : reply;
    if (value instanceof Error) {
      throw value;
    }
    return value.clone();
  });
  return { calls, route: (path, ...replies) => table.set(path, replies) };
}
