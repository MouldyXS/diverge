# Roadmap

Status: 2026-11-03. A stage is started only with the project owner's explicit approval. Component states: **design defined**, **design not ratified**, **evidence pending**, **not run**. Nothing is marked "validated" without a result.

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included.

| Stage | Content | State | Needs |
|---|---|---|---|
| General structure | Stages and direction | Accepted | — |
| **A** | Pre-change Git bundle and private backup; first commit of the draft word sets; second bundle | **Done and verified** (commit `85dd35f`; integrated recovery test passed) | — |
| **B** | Amendments and documents (this change) | **In progress**: documents written, not yet committed | Commit authorization |
| C | B1 core recapture and ratification (including t28); B2 field rules and classification; kaikki transfer | Not started | Approval per item; separate approval for the 103 MB kaikki transfer |
| D | Freeze script rewritten with atomic publication and tests; then word sets v1.0 | Not started | Approval, after B and C |
| E | Engine (`backend/app/engine`) with tests; technical measures | Not run | After D |
| F | Batteries B1a, B1b, B2–B10 | Designed, not run | After D |
| G | API and frontend, with the P0 notice | Not run | — |
| H | Informal usability tests (not a validation) | Not run | — |
| I | Licenses, publication, Docker, hosting | Not run | Own approval |

## What each stage must show before the next

- **B:** every threshold identical to the committed values (B1 90% with k = (9N + 9) // 10; B2 95%, 1,002 pairs, 952 hits; the 2c thresholds); no CSV label or state changed; no Granite run.
- **C:** the B1 core is listed with verbatim quotations, URL and date or revision; the B2 rules are ratified before any classification; every run records tool versions, resource hashes and parameters.
- **D:** the freeze script passes its tests on Windows/NTFS (failure injection at each write and at the rename, forced termination, existing target, minima for N = 4, 5, 6 and B2 = 1,002/952). Rename-based publication gives no durability guarantee on power loss.
- **E–F:** B3 and B4 pass before anything else is interpreted; the others are reported by part and relation as k/N with Wilson intervals.
- **G:** under P0 the interface shows the notice of `scoring.md` section 8, and nothing that claims validation.
- **I:** per-resource license review (`third-party-review.md`) and a decision on the repository license.

## Parked work

Human evaluation: kit v1.2 preserved, nothing collected or distributed (`future/human-evaluation.md`). Phase 2c: deferred, thresholds unchanged (`acceptance-criteria-2c.md`).
