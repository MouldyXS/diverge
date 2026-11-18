# Diverge

**English** | [Español](README.es.md)

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included. `CLAUDE.md`, cited in some historical documents, is a private project-context file and is not part of this distribution.

Diverge is a local application, **in development**, for analyzing semantic similarity and divergence between Spanish words with a multilingual embedding model run on your own machine. It is also meant to study how far the model's distances correspond to human similarity ratings by speakers of Ecuadorian Spanish.

> **Status: a first local version exists.** `backend/` holds the semantic engine, a service layer and an HTTP API v1; `frontend/` holds a React interface for it. Alongside them, the repository holds research documents, decisions and reproducible experiments. The human similarity study has not started. See [Current status](#current-status) and [Running locally](#running-locally).

## Version

**Current version: `v0.1.0-beta.1`.** This is an experimental, local beta: it runs on your own machine, it is not a hosted service, and its interface, API contract and results may change before a stable release. It is not a validated instrument.

Several things carry a version, and they are independent of one another:

| What | Identifier | Where it is declared |
|---|---|---|
| Product | `v0.1.0-beta.1` | Git tag, once the owner creates it (not created yet) |
| Frontend | `0.1.0-beta.1` (SemVer) | `frontend/package.json`, `frontend/package-lock.json` |
| Backend | `0.1.0b1` (PEP 440) | `backend/app/__init__.py` (`__version__`), also the FastAPI application version |
| HTTP API | `v1` | Route prefix `/api/v1` |
| Model | Pinned revision, `a9cb5338491faf32b73dd17b714a31821c021bbf` | `backend/app/engine`; reported by `/api/v1/model` |
| Experimental baseline | Its own identifier, e.g. `semantic_baseline_dat7_v0.1` | `experiments/results/` (not versioned in Git) |

`0.1.0-beta.1` and `0.1.0b1` are the same release written in each ecosystem's notation. The historical tag `dat-line-v0.1` marks the preserved DAT research line (`docs/decisions.md`, D21) in the private research repository; it is not a version of this product and is not part of this distribution.

## The problem

Embedding models represent words as vectors, and the angle between two vectors is often used as a measure of how close their meanings are. Whether those distances match what Spanish speakers, and in particular speakers of Ecuadorian Spanish, perceive as similar is not something a model guarantees.

Diverge aims to make those distances computable locally, inspectable and reproducible, and to contrast them with human judgments.

## How it works

1. **Embeddings.** Each word is normalized (`strip`, NFC, `casefold`, NFC) and encoded by the reference model, `ibm-granite/granite-embedding-278m-multilingual` at a pinned revision. Inference runs locally on CPU in fp32 and produces 768-dimensional vectors, L2-normalized by the model's own `Normalize` module.
2. **Similarity and distance.** For two words with vectors *a* and *b*:
   - cosine similarity `cos(a, b)` lies in [−1, 1], and higher means more similar;
   - cosine distance `d = 1 − cos(a, b)` lies in [0, 2], and higher means less similar.

   They carry the same information in opposite directions. A distance is a statement about two vectors of this model, not about the words in every context.
3. **Pairs and sets.**
   - **A pair is the main unit of analysis:** two words give one distance.
   - **A set** of *n* words yields all *n*(*n* − 1)/2 pairs, with a distance matrix and its closest and most distant pairs.
   - **The mean of a set's distances** is an **experimental indicator** of how spread its words are in this model. It is not a validated measure of anything else.
4. **DAT7.** The original research line implemented a protocol inspired by the Divergent Association Task: the first seven eligible words, 21 pairs, mean × 100. It is kept as a historical reference and an optional function, not as the center of the product.

## Limits

- **One model.** Results depend on the model, its revision and its configuration, which every result must identify. Passing reproducibility checks does not make the model the best one for Spanish, nor semantically validated.
- **Compressed range.** In the exploratory DAT7 baseline, pair distances of hand-picked "diverse" words fell between 0.17 and 0.39. Absolute values should not be read as percentages or grades.
- **Words without context.** Polysemy, regional senses, plurals and typos change distances. Antonyms can come out as close.
- **Format checks only.** Input checks cover format: one word, letters only, no repetition. They do not verify that a word exists in Spanish.
- **Small study.** Any human study planned here is small and local. It evaluates the model against human judgments and is not a psychometric validation.

## What Diverge does not measure

Diverge does not measure creativity, intelligence, originality or any cognitive ability, and it is not a validated psychometric instrument. It does not reproduce the scientific validity of the DAT and does not transfer its norms, percentiles or rankings. It is not presented as the first multilingual system for semantic-divergence analysis.

## Architecture

```
frontend/              React + TypeScript + Vite: pair analysis (main), set analysis, model panel
    │  HTTP, local only (127.0.0.1)
backend/
    app/api, app/main  FastAPI: /pairs (main), /sets, /model, /health
    app/services       AnalysisService: entry limit, one analysis at a time, service state, errors without user text
    app/engine         pure Python, no FastAPI imports: normalization, validation, embedder, distances
    │
local model cache          Hugging Face cache, pinned revision, offline; weights are never in the repository
```

The engine is usable on its own, from tests and, later, from the study's analysis scripts, which do not exist yet. The API is stateless, with no database, accounts or tracking. Human ratings, when collected, stay anonymous and outside the repository, and never pass through the engine or the API.

## Technologies

| Component | Technology | State |
|---|---|---|
| Language and environment | Python 3.12, project virtual environment `.venv` | In use |
| Inference | PyTorch (CPU build), Transformers, Sentence Transformers, NumPy | In use by the engine and the experiments; versions in `backend/requirements.txt` |
| Tests | pytest (backend); Vitest and Testing Library (frontend) | In use; versions in `backend/requirements-dev.txt` and `frontend/package.json` |
| API | FastAPI, Starlette, Pydantic, Uvicorn | In use; versions in `backend/requirements.txt` |
| Interface | React, TypeScript, Vite | In use; exact versions in `frontend/package.json` and `frontend/package-lock.json` |
| Packaging | Docker, last, with the model weights in a volume or cache | Planned |

## Current status

| Component | State | Where |
|---|---|---|
| Project decisions and scope | **Existing** | `docs/decisions.md` (D21 is the current scope) |
| Technical checks of the model: loading, pooling, normalization, reproducibility | **Existing**, Phase 2a PASS | `experiments/embedding_poc/`, `experiments/check_2a_correctness.py` |
| Lexical adjudication (D19) and regional inventory (D20), with validators and tests | **Existing** in the research repository; not included in this distribution | `experiments/semantic_2b/evidence/`, `experiments/wordsets/regional/` (private research repository, not part of this distribution) |
| DAT7 baseline and B3/B4 diagnostics | **Experimental**, exploratory, on draft word sets; verified against private data, not included in this distribution; outputs not versioned, with private backups | `experiments/results/` |
| DAT research line, preserved | **Historical**; preserved in the private research repository (tag `dat-line-v0.1`), not included in this distribution | `docs/phase-2b-design.md`, `docs/acceptance-criteria-2c.md`, `docs/scoring.md`, `docs/roadmap.md` |
| Semantic engine and its tests, including the DAT7 baseline regression (it needs private reference files, not included, and runs only with `--baseline`) | **Existing** | `backend/app/engine/`, `backend/tests/` |
| Service layer (`AnalysisService`) | **Existing** | `backend/app/services/` |
| HTTP API v1: `/health`, `/model`, `/pairs`, `/sets` | **Existing**; local only, no authentication or persistence | `backend/app/api/`, `backend/app/main.py` |
| Interface: pair and set analysis, distance matrix, backend state | **Existing**; its automated tests use a synthetic embedder. On 2026-11-06 it was also run once, locally and end to end, with the real Granite model: pair and set analyses, input-error cases and the model panel worked through the API. That run had no predefined acceptance thresholds | `frontend/` |
| Human similarity study | **Planned**; no data collected; requires design and institutional requirements first | `docs/decisions.md` D21, `docs/future/human-evaluation.md` |

Installation and run instructions are in [Running locally](#running-locally). The experiments document their own commands: see `experiments/embedding_poc/README.md`. The interface shows the notice that Diverge only checks the format of the input (`docs/scoring.md` §8); none of its results is a validated measure of creativity or of any other construct.

## Getting the model

The model weights are not in the repository. Download the pinned revision once (about 544 MiB, nine files). Granite Embedding 278M Multilingual is licensed Apache-2.0 according to the model card of that revision; the tokenizer's license has not been verified separately. After the download the application works offline (`HF_HUB_OFFLINE=1`, `local_files_only=True`) and downloads nothing at startup. When it loads the model, the engine requests the pinned revision from the local cache only and checks its modules, pooling, dimension, dtype and device. The SHA-256 of `model.safetensors` is checked by the tests marked `model` (`pytest -m model`, with the model downloaded), not at startup.

The `hf` executable comes with `huggingface_hub`, which `backend/requirements.txt` installs. Activate the virtual environment where you installed it (for example `.\.venv\Scripts\Activate.ps1`) or call it by its path (`.\.venv\Scripts\hf.exe`). The two commands below are independent, with the same revision and the same nine file names. **A downloads nothing; B does download.**

A. Dry run (downloads nothing):

```powershell
hf download `
  --revision a9cb5338491faf32b73dd17b714a31821c021bbf `
  --dry-run `
  ibm-granite/granite-embedding-278m-multilingual `
  "1_Pooling/config.json" `
  "config.json" `
  "model.safetensors" `
  "modules.json" `
  "sentence_bert_config.json" `
  "sentencepiece.bpe.model" `
  "special_tokens_map.json" `
  "tokenizer.json" `
  "tokenizer_config.json"
```

B. Download (the same command without the `--dry-run` line):

```powershell
hf download `
  --revision a9cb5338491faf32b73dd17b714a31821c021bbf `
  ibm-granite/granite-embedding-278m-multilingual `
  "1_Pooling/config.json" `
  "config.json" `
  "model.safetensors" `
  "modules.json" `
  "sentence_bert_config.json" `
  "sentencepiece.bpe.model" `
  "special_tokens_map.json" `
  "tokenizer.json" `
  "tokenizer_config.json"
```

## Running locally

Two processes on the same machine, each in its own terminal. Details: [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md). Tested on Windows only: the example commands use PowerShell and Windows paths such as `..\.venv\Scripts\python.exe`.

0. First time only, from the repository root: create the virtual environment `.venv` with Python 3.12 and install the backend dependencies (`requirements-dev.txt` also installs the test tools):

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
   ```

   Then download the model ([Getting the model](#getting-the-model)) and run `npm ci` in `frontend/`. The backend tests that need neither the model nor private data run from `backend/` with `..\.venv\Scripts\python.exe -B -m pytest -m "not model"` (`backend/README.md`, Tests).

1. Backend, from `backend/` (Python 3.12 in `.venv`; the model must already be in the local Hugging Face cache, see [Getting the model](#getting-the-model)):

   ```powershell
   ..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --lifespan on --loop asyncio --http h11 --no-access-log --timeout-graceful-shutdown 10
   ```

2. Interface, from `frontend/` (Node 24.15 or later; `npm ci` the first time):

   ```powershell
   npm run dev
   ```

   Then open `http://127.0.0.1:5173`.

## Licenses and third parties

No license is granted by this repository for its original materials at this time. No general permission to reuse, modify, or redistribute those materials is granted. Third-party components remain subject to their respective licenses; see `NOTICE` and `THIRD_PARTY_NOTICES.md`, and `docs/third-party-review.md` for the detailed review.

## AI assistance

AI tools were used during development:

- **ChatGPT** (OpenAI) helped draft the initial project-context document, which is not part of this distribution, and the instructions given to the coding assistant.
- **Claude Code** (Anthropic) generated and modified code, tests and documentation during the implementation, following those instructions.

The project owner set the goals and scope, made the project decisions and authorized each stage of the work. This section describes how the project was built; it does not attribute authorship or rights to any AI tool.
