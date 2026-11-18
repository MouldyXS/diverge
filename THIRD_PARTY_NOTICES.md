# Third-party notices

Status: 2026-11-18. **A record of what was checked locally, not legal advice.** This repository does not include, vendor or redistribute any of the third-party software, models or data listed here: Python packages are installed into a local virtual environment, npm packages into `frontend/node_modules/`, the model is downloaded to the local Hugging Face cache, and the lexical resources were consulted. Each keeps its own license and notices. No license is granted by this repository for its original materials (`NOTICE`). The detailed review, with what remains pending, is `docs/third-party-review.md`.

## Embedding model

| Item | Value | How it was checked |
|---|---|---|
| Model | `ibm-granite/granite-embedding-278m-multilingual` (IBM) | Pinned in `backend/app/engine/embedder.py` and `experiments/embedding_poc/embedding.py` |
| Revision | `a9cb5338491faf32b73dd17b714a31821c021bbf` | Name of the local snapshot directory |
| Weights | `model.safetensors`, SHA-256 `b522423ae15d1a6fd48c55ef4f599c0c2c0737603da94e4b4815760c2c06ebac` | Recorded in `experiments/results/embedding_poc_2a/manifest.json` and `backend/tests/test_baseline_regression.py` |
| License | Apache-2.0, according to the model card | `docs/third-party-review.md`, checked online on 2026-11-03. **Not verifiable locally:** the cached snapshot contains no model card and no license file |
| Training data note | MS-MARCO excluded from training because of its non-commercial license | Same source |

The weights are not in the repository and are not redistributed.

## Python packages

Direct dependencies, pinned to exact versions in `backend/requirements.txt` (runtime) and `backend/requirements-dev.txt` (adds the test tools). Package names are as written in those files. Licenses are as declared in each package's installed metadata (`License-Expression` or `License` field, or the license classifier), read locally on 2026-11-18 from an environment with those exact versions; they were not checked against each package's full license text.

### Runtime: `backend/requirements.txt`

| Package | Version | License as declared |
|---|---|---|
| `numpy` | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `torch` (CPU build, from the PyTorch CPU index) | 2.15.0+cpu | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib; bundles third-party license files |
| `sentence-transformers` | 6.2.0 | Apache-2.0; ships a `NOTICE.txt` naming the UKP Lab of Technische Universität Darmstadt (2019–2025) and Hugging Face, Inc. (2025–present) |
| `transformers` | 5.22.1 | Apache 2.0 License (`License` field) |
| `huggingface-hub` | 2.4.0 | Apache-2.0 |
| `tokenizers` | 0.23.3 | Apache Software License (classifier only; no license file in its metadata) |
| `fastapi` | 0.162.0 | MIT |
| `starlette` | 1.9.0 | BSD-3-Clause |
| `pydantic` | 2.14.1 | MIT |
| `uvicorn` | 0.54.0 | BSD-3-Clause |

### Development and tests: `backend/requirements-dev.txt`

| Package | Version | License as declared |
|---|---|---|
| `pytest` | 9.2.0 | MIT |
| `httpx2` | 2.16.0 | BSD-3-Clause. Used by Starlette's `TestClient`. The package is named `httpx2`; it requires `httpcore2` 2.16.0 (BSD-3-Clause) |

Transitive dependencies are installed by pip and are not listed individually. `backend/environment.freeze.txt` is a snapshot of the development environment, not a list of notices.

### Experiments and other packages of the development environment

`experiments/embedding_poc/requirements-poc.txt` pins a subset of the runtime packages above (`torch`, `transformers`, `sentence-transformers`, `numpy`, `huggingface_hub`, `tokenizers`) and `pytest`, at the same versions.

| Package | Version | License as declared | Role |
|---|---|---|---|
| safetensors | 0.8.0 | Apache Software License (classifier) | Installed as a dependency of the packages above |
| scipy | 1.18.1 | BSD License (classifier) | Installed; not used directly by the project |
| wordfreq | 3.1.1 | Code Apache-2.0. Some of its data is under CC BY-SA 4.0 (see below) | Used only by experimental tooling of the private research repository, not part of this distribution |

Redistribution, for example in a Docker image or a packaged build, would need the full notices of each package, including the `NOTICE.txt` of sentence-transformers.

## npm packages

Direct dependencies, with exact versions, in `frontend/package.json`; `frontend/package-lock.json` (lockfile version 3) pins 147 packages in total. Licenses are as recorded in the `license` field of `package-lock.json`, read on 2026-11-18; they were not checked against each package's license file.

### Runtime: `dependencies`

| Package | Version | License as declared |
|---|---|---|
| `react` | 19.1.10 | MIT |
| `react-dom` | 19.1.10 | MIT |

The only other non-development package in the lockfile is `scheduler` 0.26.0 (MIT), a dependency of `react-dom`.

### Development: `devDependencies`

| Package | Version | License as declared |
|---|---|---|
| `@testing-library/dom` | 10.4.2 | MIT |
| `@testing-library/react` | 16.3.3 | MIT |
| `@types/react` | 19.3.0 | MIT |
| `@types/react-dom` | 19.3.0 | MIT |
| `@vitejs/plugin-react` | 6.1.2 | MIT |
| `jsdom` | 30.1.3 | MIT |
| `typescript` | 7.0.2 | Apache-2.0 |
| `vite` | 8.3.5 | MIT |
| `vitest` | 4.1.12 | MIT |

A production build (`npm run build`, written to `frontend/dist/`, which Git ignores) bundles code from the runtime packages. No build is included in this repository; distributing one would need their notices.

## Lexical resources consulted

Consulted in the private research repository to build and document the DAT line's draft word sets and evidence. Their data, and the word sets, evidence tables and regional inventory built from them, are not part of this distribution (`docs/third-party-review.md`).

| Resource | Recorded license or state | Pending |
|---|---|---|
| Multilingual Central Repository (`omw-es:2.0`) | CC BY 3.0, per the package `LICENSE` | Equivalence with MCR 3.0 not confirmed |
| Princeton WordNet (`omw-en:2.0`) | WordNet License 3.0, per the package; its notice and disclaimer must accompany copies | Text on the project site not read |
| Wiktionary (Spanish edition), and the kaikki.org extraction | CC BY-SA 4.0, as stated in the footers of the entries checked; Wikimedia terms. kaikki refers to the Wiktionary licenses | Each cited entry |
| wordfreq data | Some data under CC BY-SA 4.0 (wordfreq README) | ShareAlike reading; sources with no stated license. Data and derived values stay out of Git |
| DAMER (ASALE / RAE) | **Unresolved:** legal notice not read | Reuse conditions |
| *Diccionario académico de ecuatorianismos* (Academia Ecuatoriana de la Lengua, 2023) | Read in the official PDF | Reuse conditions |

spaCy and its GPL-3.0 Spanish models are excluded from the project.
