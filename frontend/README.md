# Diverge frontend

A local web interface for Diverge's HTTP API v1, written with React, TypeScript and Vite. It only presents what the API returns: it computes no embedding, applies no normalization, no P0 rule and no token count, and it never changes or rounds a received value (numbers are displayed with four decimals; the exact value is available on hover and in the matrix detail).

## Requirements

- Node.js 24.15 or later (tested with 24.19.0) and npm 11 (tested with 11.17.0). `jsdom`, used by the tests, needs Node `^24.15`.
- The Diverge backend running locally (see `backend/README.md`).

## Install

From `frontend/`:

```powershell
npm ci
```

`package-lock.json` pins every package; `npm ci` reproduces it exactly. Direct dependencies, all with exact versions:

| Package | Version | Use |
|---|---|---|
| `react`, `react-dom` | 19.1.10 | Interface |
| `vite` | 8.3.5 | Development server and build |
| `@vitejs/plugin-react` | 6.1.2 | JSX and fast refresh |
| `typescript` | 7.0.2 | Type checking (`tsc --noEmit`) |
| `@types/react`, `@types/react-dom` | 19.3.0 | Types |
| `vitest` | 4.1.12 | Tests |
| `jsdom` | 30.1.3 | DOM for the tests |
| `@testing-library/react`, `@testing-library/dom` | 16.3.3, 10.4.2 | Component tests |

No HTTP, state, routing, CSS or chart library: requests use the Fetch API, state uses React (`useReducer` and one Context), and styles are plain CSS (`src/styles/`).

## Run

1. Start the backend from `backend/`:

   ```powershell
   ..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --lifespan on --loop asyncio --http h11 --no-access-log --timeout-graceful-shutdown 10
   ```

2. Start the interface from `frontend/`:

   ```powershell
   npm run dev
   ```

3. Open `http://127.0.0.1:5173`.

The development server and `npm run preview` both use `127.0.0.1:5173` with a fixed port: if the port is taken they stop instead of moving to another one, because the backend's CORS policy allows only `http://localhost:5173` and `http://127.0.0.1:5173`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `VITE_DIVERGE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Base URL of the API; the only HTTP destination of the interface |

Copy `.env.example` to `.env` to change it. Vite reads it at start-up and build time.

## What the interface does

- **Backend state.** On start it asks `/health` and `/model` once, in parallel, and shows: connecting, available, service failed, service stopping, backend unreachable, or metadata unavailable. A 503 from `/health` is a service state, not a network failure. There is no polling: a button checks again, and the state is checked once more after an analysis fails for a network, timeout or service reason.
- **Limits.** `max_words` and `max_input_tokens` come only from `/model`. Without metadata, no row can be added (no limit is guessed); analyses are still sent, and the backend applies its limit.
- **Pair.** Two fields, sent exactly as typed. The result shows the normalized words, similarity, distance on its fixed range [0, 2], a descriptive reading and the model identity, and the P0 notice.
- **Set.** Starts with three rows; rows can be added (up to `max_words`), removed, or replaced by pasting several lines (split on line breaks only, without trimming). Every row is sent, empty or repeated ones included, so the engine reports them.
- **Descriptive reading.** Under the numbers of a result, a short impersonal text in Spanish describes what the model computed, plus a separate "Cómo leerlo" block with the warnings. For a pair it is written in the browser from `PairResponse` (similarity, distance and what they are, with no percentage of the theoretical range and no category). For a set it is written from the `interpretation` facts of `/sets`: number of concepts and pairs, mean (experimental indicator), smallest and largest distance with their pairs and the range, ties (told apart as equal at the shown four decimals or exactly equal; at most five pairs listed, then "y N más"), and how many pairs are above, below or equal to the mean of that set. Comparisons are only relative ("mayor", "menor", "por encima de la media"); it makes no claim about creativity, other people or reference values, and it is not part of the P0 notice. The templates are in `src/copy.ts` and the composition in `src/interpretation/describe.ts`.
- **Matrix.** Rebuilt from `words` and the pairs' 0-based `i`, `j`: each distance is placed in both symmetric cells and the diagonal is "not applicable". An incoherent response is reported, not drawn. Colors use a scale relative to the current set (labelled with its minimum and maximum); values are written in the cells up to 12 words. The matrix has a single tab stop and is navigated with the arrow keys; the pair table, sortable by distance, is the full accessible alternative.
- **Errors.** Every API code and rejection reason has a Spanish text in `src/copy.ts`; the backend's English messages are never shown. Network errors, timeouts, API errors and unexpected answers look different. `analysis_busy` enables a manual retry after its `Retry-After`. The request ID is shown under "Detalles técnicos".
- **Concurrency.** The backend admits one analysis at a time. In a browser tab, only one analysis runs at a time across both modes, and double submissions are ignored; another client may still get the service busy, which the interface reports.
- **Timeouts.** 10 s for `/health` and `/model`, 60 s for analyses. An expired analysis is reported as unconfirmed: the backend may still be processing it, so check its state before retrying. Nothing is retried automatically.
- **Privacy.** No storage (no `localStorage` or cookies), no analytics, no CDN or external fonts, no words in URLs (analyses use POST), no console output, and no HTTP destination other than the configured API.

### Pending: P0 notice wording

The P0 notice is shown with every result, verbatim from `docs/scoring.md` section 8 (decision D14). Its third paragraph speaks of "El índice", which belongs to the DAT line and does not exist in the pair mode. The text is kept literally until the project owner decides otherwise.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Development server on `127.0.0.1:5173` |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Unit and component tests (Vitest, jsdom); no backend needed |
| `npm run test:integration` | Checks the shapes of real API responses; needs a running backend (any embedder; it checks shapes, not numbers) |
| `npm run build` | Type check and production build into `dist/` |
| `npm run preview` | Serves `dist/` on `127.0.0.1:5173` |

## Layout

```
src/
  main.tsx, App.tsx      entry point, header, tabs
  copy.ts, format.ts     every Spanish text (with the literal P0 notice); number display
  api/                   client.ts (the only module that calls fetch), types.ts (API contracts), errors.ts
  backend/               BackendProvider (state, metadata, one-analysis slot), BackendStatus, ModelPanel
  pair/                  pair form, result and reducer
  interpretation/        describe.ts (sentences from the facts), pair and set reading components
  set/                   set form, results, matrix (matrix.ts rebuilds it), pair table and reducer
  components/            error panel, entry errors, P0 notice, model badge, distance bar
  styles/                design tokens and styles
  test/                  test setup, fixtures, fetch stub
  integration/           integration test (npm run test:integration)
```
