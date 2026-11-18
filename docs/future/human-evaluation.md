# Future work: evaluation with human participants

Status: **postponed on 2026-11-03, not discarded.** Nothing has been collected or distributed, and the MVP does not depend on it. This file says what is preserved and what a future evaluation would have to settle first.

> **Note on this distribution.** The review kit cited below is not part of this distribution.

## Why it is postponed

Diverge is a personal portfolio project. Recruiting participants (including speakers of Ecuadorian Spanish), institutional requirements and data handling are out of scope for the MVP. The project instead uses computation, software tests and source-backed word sets (`../evaluation-strategy.md`). This does not make human evidence unnecessary: without it, evidence level E3 is **not claimed**.

## What is preserved

The kit (version 1.2) lives under `experiments/results/lexical_audit_v0.1/human_review/`. That folder is not versioned: Git ignores most of it, and it is held in a private backup outside the repository.

| Part | What it is |
|---|---|
| 23 fichas | 19 triplets from the lexical audit plus 4 provisional reference items, with opaque codes |
| 8 main booklets (P01–P08) | Constrained-random plan, seed 20261103; every pair role in each position 2 or 3 times; anchor 4 times on each side |
| Reserve P09–P11, usability booklet P12 | Reserve = copy of a lost booklet's order; P12 is a usability test, outside the analysis |
| `key/` | Item key, plan, assignment sequence, manifest with hashes (administrator only) |
| Scripts | `build_human_review.py`, `verify_kit.py` (38 checks), `check_transcription.py`, `balance_metrics.py`, and others |
| Documents | Participant instructions, draft consent statement, administrator notes, analysis procedure and limitations |

## What a future evaluation must settle before any use

1. **Institutional requirements** of any organization through which participants might be recruited, including any applicable ethics review, and a completed consent statement. The draft states it is not an approved document.
2. **Which rows.** The 19 rows were chosen by an audit that has since been repeated with different tooling; check them against the ratified B1 core.
3. **Data handling.** Participant data stays outside the application and the core engine. No profiles, no tracking, no identity-to-code table.
4. **Usability test with P12**, repeated if a change alters what participants see.
5. **Analysis.** Descriptive only, as in `analysis_procedure_and_limitations.md`; human results do not become acceptance thresholds and do not alter B1 or B2.
6. **Transcription.** A second person transcribes every booklet independently.

## Limits that would remain

Small convenience sample, ordinal five-level scale, no test–retest, a single investigator, isolated words without context. At most this is face plausibility (E1) over a few triplets, not criterion validity (E3).
