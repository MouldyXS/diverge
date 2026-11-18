# Evaluation strategy

Status: 2026-11-03. Design accepted by the project owner; nothing in sections 3 to 5 has been run. Labels: **FACT**, **PROPOSAL**, **UNCERTAIN**.

**Scope note (2026-11-06, D21).** This strategy was written for the DAT line and is kept as written, apart from the definition of H1 in section 2. Under D21 the project adds a study of correspondence between model distances and human similarity ratings, labeled **H1**. H1 is not E3: it does not test whether any score measures creativity or another psychological construct.

## 1. Purpose and limits

Diverge is a personal portfolio project: a public web application that returns a semantic divergence index for ten words. This strategy says what evidence the project can produce about that index **without human participants**, and what it cannot.

- Evaluation with human participants is **postponed, not discarded** (`future/human-evaluation.md`).
- Evidence level E3 (criterion validity with human data in Spanish) is **not performed and never claimed**. Nothing here makes Diverge a validated instrument or a measure of creativity.
- Raw Granite scores are not comparable with DAT or S-DAT scores, and no percentile or population norm is shown (`scoring.md`).

## 2. Evidence levels used

| Level | Source of evidence in this strategy | Status |
|---|---|---|
| E0 technical correctness | Phase 2a checks; unit and API tests; mathematical properties (section 3) | 2a done; the rest not run |
| E1 face plausibility | B1a/B1b on a curated, source-backed core; B7, B8 examples | Not run |
| E2 robustness | B2–B6, B9, B10; invariance and normalization | Not run |
| E3 criterion validity | Requires human data. Validity of the index as a measure of a psychological construct such as creativity | Not performed; never claimed |
| H1 human similarity correspondence (D21) | Correspondence between model distances and human ratings of semantic similarity by speakers of Ecuadorian Spanish. Evidence about the model, not validity of creativity; outside E0 to E3 | Planned; no data collected |

## 3. Mathematical and technical checks (E0)

- **Range.** Cosine distance lies in [0, 2], so the index lies in [0, 200]. Tests confirm that no calculation leaves that range.
- **Properties of the distance.** Symmetry, zero distance for identical vectors and the stated range are tested. Cosine distance is not claimed to satisfy the triangle inequality.
- **Counts.** `dat7` produces 21 pairs for 7 words; `all10` (experimental only) 45 pairs for 10.
- **Phase 2a (done, `experiments/results/2a_20261103_004339/manifest.json`).** Agreement of Sentence Transformers with the reference CLS + L2 implementation (cosine at least 0.99999), effective attention implementation recorded and not Flash Attention 2, reproducibility within 1e-6, CPU build of torch. Pinned model revision `a9cb5338491faf32b73dd17b714a31821c021bbf`.
- **Reproducibility.** Every run writes a manifest with library versions, model revision, device, attention implementation, seeds, word-set hashes and the Git commit.

## 4. Computational-semantic batteries (E1–E2; designed, not run)

All use curated word sets with cited sources. They run only after the word sets are frozen (`roadmap.md`, stages C and D). Details and thresholds are in `phase-2b-design.md` and `acceptance-criteria-2c.md`.

| # | Battery | Entries | Threshold |
|---|---|---|---|
| B1a | `d(anchor, close) < d(anchor, related)` on the curated core | N between 4 and 6, fixed at Stage C | 90%, k = (9N + 9) // 10 |
| B1b | `related` vs `unrelated` candidates | All triplets | None; descriptive |
| B2 | Single-field vs mixed-field sets | 6 evaluation fields × 167 = 1,002 pairs | 95%, at least 952 hits |
| B3 | Invariance: order, NFC/NFD, case | 200 seeded sets | Difference < 1e-6; blocks if it fails |
| B4 | Six diacritic pairs (sí/si, él/el, año/ano, papá/papa, té/te, sé/se) | 6 pairs | Distinct, both embedded, d ≥ 1e-6; blocks if it fails |
| B5 | Distribution of pair distances and of the index; between-field matrix | 10,000 sets | Reference of this group of words, not a norm |
| B6 | `dat7` vs `all10` | 1,000 sets | None |
| B7 | Entry order and substitution of an invalid word | 14 draft sets | Examples only |
| B8 | Edge cases | 52 rows | Descriptive; no claim about regional use |
| B9 | Invented strings | 6 strings | Informative |
| B10 | Frequency control with wordfreq (local, descriptive) | Subsets matched by Zipf band | No recalibration after the results |

**How to read a result.**

- A pass is plausibility, not validation. A fail on B1a/B1b or B2 does not refute Granite on its own: first inspect the failing rows (a label may be wrong), and record any change with its reason.
- B1a is an exploratory benchmark of a few rows; a definition that mentions a concept does not predict a distance.
- B2 observations are not independent (the same words are reused); intervals are descriptive and optimistic.
- Every proportion is reported as k/N with a Wilson 95% interval; thresholds are not changed after results.

## 5. Software tests (Stage E onward)

- **Engine** (`backend/app/engine`, no FastAPI imports): normalization, deterministic validation, scoring on fixed vectors, protocol rules (fewer than seven eligible words gives no score).
- **API:** schemas, errors, and the output contract of `scoring.md`.
- **Regression:** golden values for a few sets with the pinned model, so a dependency change is noticed.
- **Frontend:** component and flow tests for the timer, entry validation feedback and the results screen.

## 6. Usability tests (Stage H)

Informal sessions on the working application: are the instructions clear, can people finish within four minutes, is the result readable, does the P0 notice get read. They are **not a validation**, collect no participant profiles and are not used to adjust the index.

## 7. What the project may and may not say

| May say | May not say |
|---|---|
| "Semantic divergence index computed with a multilingual embedding model" | That it measures creativity, intelligence or personality |
| "Behaves plausibly on a small curated set (B1a/B2), with these limits" | That it is validated, or equivalent to the DAT or S-DAT |
| "Raw score of this model; no norm" | Percentiles, rankings or population averages |
| "Checks the format of the entries only (P0)" | That it checks that a word exists or is a noun |
