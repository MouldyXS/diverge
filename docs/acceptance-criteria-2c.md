# Acceptance criteria for Phase 2 (fixed 2026-11-03; see the amendment log in section 7)

> **Status: values confirmed by the project owner on 2026-11-03 (decision D11) and committed in `be34d50`; the amendments in section 7 are introduced by the commit "docs: finalize pre-experiment acceptance criteria".** This file must be **committed before the first Phase 2c evaluation run**. The commit hash is recorded in each 2c `manifest.json`. After that commit, changing a threshold requires a new commit with a written reason and invalidates earlier 2c results.
>
> Confirmed without change: false negatives ≤ 15% for regionalisms, false positives ≤ 5% for nonexistent strings, manipulation effect ≤ 0.5 SD. Changed: minimum sample sizes were reduced (section 2).

> **Amendment 3 (2026-11-03, section 7).** B1 is split into B1a and B1b, and Phase 2c is deferred. **No threshold changes.** The B1 core composition and the B2 field rules are not yet ratified. Sections 4.1 and 5 keep their original wording; read them with amendment 3.

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included. `CLAUDE.md`, cited in some historical documents, is a private project-context file and is not part of this distribution.

All criteria are **experimental criteria (evidence levels E0–E2)**, not scientific validation. See CLAUDE.md §10 (a private project-context file, not part of this distribution); the evidence levels are in docs/evaluation-strategy.md, section 2.

## 1. Data partition

- Word sets are split into **development** and **evaluation** parts before any threshold or rule is chosen.
- Proposed split: 50/50, stratified by category and region, with a fixed seed (proposed seed `20261102`, recorded in the manifest).
- Words are grouped by `family_id` (lemma / lexical family, e.g. singular and plural) so no family appears on both sides.
- Development part: sweep of the Zipf threshold `t`, choice of rules, choice of input format (bare word vs template). Evaluation part: used **once**, with frozen parameters. Re-using it requires a new evaluation fold.

## 2. Minimum labeled sample sizes

| Category | Minimum labeled words (total, both partitions) |
|---|---|
| Common valid nouns | 150 |
| Regionalisms, Ecuador | 40 |
| Regionalisms, other countries (pooled, at least 4 countries) | 60 |
| Nonexistent strings and pseudo-words | 100 |
| Proper nouns | 40 |
| Verbs and adjectives | 40 |
| Specialized terms | 40 |
| Typos | 40 |
| Plural forms | 40 |

About half of each total falls in the evaluation part, so the regionalism estimates will have wide Wilson intervals (with about 20 Ecuadorian words, the 95% interval is roughly ±15 to 20 points). The report states this, and a pass on a wide interval is not described as strong evidence.

If a category falls short of its minimum, its result is reported but excluded from the policy decision, and this is stated in the report.

## 3. Phase 2a — technical correctness (E0)

| Check | Criterion |
|---|---|
| Sentence Transformers vs reference (first token + L2 normalization, Transformers) | cosine ≥ 0.99999 for every test word |
| Effective attention implementation | recorded in the manifest; must not be Flash Attention 2 |
| Reproducibility | same input gives the same vector within 1e-6: same session, new process, different batch composition and order |
| Torch build | `torch.version.cuda` is `None` (CPU build) |

Failure of any check blocks Phase 3 until diagnosed.

## 4. Phase 2b — semantic behavior (E1–E2)

| Check | Criterion (reported for each partition separately; decisions use development; the triplet threshold applies as in section 4.1) |
|---|---|
| Triplet ordering: close word < related < unrelated | at least 90% of the criterion triplets of the **evaluation part only** (section 4.1) |
| Single-field sets score lower than mixed-field sets | at least 95% of the observations of the **evaluation part only** (section 4.2) |
| Order invariance, NFC vs NFD, case | index differs by less than 1e-6 |
| Normalization cases (sí/si, él/el, año/ano, papá/papa, té/te, sé/se) | each pair treated as distinct words; both can be scored; only a warning is issued |
| Empirical range and pair-distance histogram | reported; no threshold. Flag if the SD of the random-baseline index is below 1 point |
| `dat7` vs `all10` sensitivity | Spearman correlation and absolute differences reported; no threshold |

### 4.1 Triplet ordering criterion

> **Superseded for B1 by amendment 3 (section 7).** The text below is the original criterion, kept for the record. The 90% threshold and the formula k = (9N + 9) // 10 are unchanged; the denominator, the inequality tested and the partition are replaced by B1a.

- **Correct triplet:** d(anchor, close) < d(anchor, related) < d(anchor, unrelated), both inequalities strict. A tie counts as incorrect.
- **Criterion denominator:** the 37 semantic-proximity triplets, namely 20 `synonym` and 17 `near_synonym`. The other 13 (`anchor_is_kind_of_close`, `close_is_kind_of_anchor`, `abbreviation`, `part_or_unit`) are evaluated and reported separately and are never part of this denominator.
- **Where it applies:** the 90% threshold applies **exclusively to the evaluation part**. Development and evaluation results are never combined for this criterion.
- **Stratification:** the split is made within each relation, so `synonym` and `near_synonym` keep their proportions in both parts.
- **Minimum number of correct triplets:** the smallest integer k with k/N ≥ 0.90, computed with integer arithmetic as k = (9N + 9) // 10 for the exact evaluation size N.

| Part | `synonym` | `near_synonym` | N | Minimum correct for the criterion | At that minimum (Wilson 95%) |
|---|---|---|---|---|---|
| Evaluation | 10 | 9 | 19 | **18** (18/19 = 94.7%; 17/19 = 89.5% does not pass) | 75.4%–99.1% |
| Development | 10 | 8 | 18 | Not applicable: the threshold is not applied here | Not applicable |

These sizes assume no triplet is rejected or relabeled during review. If that happens, N and the minimum are recalculated at freeze, before any results exist, with the same formula, and recorded in the word-set manifest. The 90% threshold does not change.

- **Reporting:** for each part separately, the global criterion result and each subcategory (`synonym`, `near_synonym`, and each of the four other relations), as k/N with a Wilson 95% interval. Subcategories have no threshold of their own.

### 4.2 Single-field vs mixed-field criterion (B2)

- **Unit of observation:** one *pair* (S, M), where S is a single-field set and M is a mixed-field set, both of 7 words from the evaluation part, scored with the `dat7` index (21 pairwise distances). Validation is not involved: all words come from the curated pool.
- **Single-field set S:** 7 distinct words drawn from one evaluation field f.
- **Mixed-field set M:** one word from each of the **six evaluation fields** plus one word from the evaluation half of the general nouns. The word taken from field f is drawn from the 8 words of f that are not in S, so S and M share no word. **Development fields and development general nouns never appear in any evaluation set.**
- **Hit:** index(S) < index(M), strict. A tie counts as a miss.
- **Denominator:** N = 6 evaluation fields × 167 pairs per field = **1,002**. The 167 pairs of each field are seeded draws without repeating the same (S, M) combination. Sample-size justification (accepted by the project owner): a balanced design with exactly 167 pairs in each of the six evaluation fields is preferred over 1,000 pairs with a slightly unequal split (four fields with 167 and two with 166), so no field weighs more than another in the pooled result. The number is a design choice, not a statistical power calculation. The seed is 20261102 with a distinct spawn key recorded in the manifest; the pairs generated are saved and their hash is recorded.
- **Minimum number of hits:** ceil(0.95 × N), computed with integer arithmetic as k = (95N + 99) // 100. For N = 1,002 the minimum is **952** (952/1,002 = 95.01%; 951/1,002 = 94.91% does not pass).
- **Where it applies:** the 95% threshold counts only the evaluation part. Development results (same procedure, development fields only) are used to debug the procedure and take methodological decisions, are labeled "development", and never count toward the 95%.
- **Reporting:** the global k/N and the k/n of each of the six fields are always both reported, with Wilson 95% intervals. Per-field results have no threshold of their own. At the minimum, the Wilson interval is 93.5%–96.2%; it is a **descriptive reference under the assumption of independence, not conclusive statistical evidence** (see the limitation below).
- **Limitation (independence):** the observations are not independent. Each field has 15 words, so the 167 single-field sets of a field reuse the same words, and mixed sets reuse the same 61 general nouns and the same words of the other fields. The 1,002 pairs are **not** 1,002 independent observations: in effect the data hold six fields. The Wilson intervals assume independence and are therefore **optimistic**; the report says so and gives the per-field results next to the pooled one.
- If a field or general noun is rejected or relabeled in review, N and the minimum are recalculated at freeze, before any results exist, with the same formula, and recorded in the word-set manifest. The 95% threshold does not change.

## 5. Phase 2c — validation policy (E1–E2)

> **Deferred (amendment 3).** Every threshold below is unchanged. If Phase 2c is run later, this section and its decision rule apply as written. P0 is meanwhile a provisional product decision, not a result of this section.

Computed **on the evaluation part**, with Wilson 95% intervals. A policy is *acceptable* only if every criterion holds for the point estimate; the upper or lower Wilson bound is reported next to it.

| Metric | Criterion |
|---|---|
| False negative rate, common valid nouns | ≤ 2% |
| False negative rate, Ecuadorian regionalisms | ≤ 15% |
| False negative rate, other regionalisms (pooled across countries) | ≤ 15% (per-country rates are reported, without a threshold) |
| False positive rate, nonexistent strings and pseudo-words | ≤ 5% |
| Score manipulation: replacing one valid word by a nonexistent string in a `dat7` set | median increase of the index ≤ 0.5 × the SD of the random-baseline index |

Notes:

- "False negative" means a legitimate word rejected, left out of the seven, or flagged as needing confirmation. For P2 the unconfirmed state counts as a false negative; the report also gives the rate after confirmation.
- P2 is reported in two scenarios: the user confirms only valid words, and the user confirms everything. In the second scenario P2 is equivalent to P0 for protection against invalid words.
- Heuristics for verbs/adjectives, proper nouns and specialized terms are **advisory**. They are kept only if precision and recall on the evaluation part are reported; they have no pass/fail threshold because they never block.
- The Zipf threshold `t` is chosen on the development part as the value that satisfies the criteria with the largest margin; ties go to the lower `t`.

### Decision rule

1. Discard policies that fail any criterion.
2. Among the remaining policies, prefer the lower false-negative rate for regionalisms, then the simpler policy (P0 < P2 < P1).
3. If no policy passes, adopt none: record the result and reconsider the validation design before Phase 3.
4. D3 is decided at the checkpoint after 2c, citing this file's commit hash.

## 6. Out of scope

No claim of criterion validity (E3) is made from any of these results.

## 7. Amendment log

- **2026-11-03 (commit "docs: finalize pre-experiment acceptance criteria"), section 4.2.** Defines the unit of observation, the hit, the denominator (N = 1,002) and the minimum number of hits (952) for the single-field vs mixed-field criterion, and limits it to the evaluation part. Reason: the criterion had no stated unit, denominator or partition, and the earlier wording of the design (1,000 pairs per part, mixed sets of "7 different fields") did not match the 6-field partition. The 95% threshold is unchanged. The change from 1,000 to 1,002 pairs only equalizes the six fields (exactly 167 pairs each): the project owner chose a balanced distribution over 1,000 pairs with an unequal split. The minimum of 952 hits is kept. The word sets, their composition and every threshold are untouched, and the dry run checks that each field has exactly 167 pairs and that the total is 1,002. Made by the project owner before any Phase 2b or 2c experiment has been run; only the Phase 2a technical checks exist.
- **2026-11-03 (commit "docs: finalize pre-experiment acceptance criteria"), section 4.1.** Defines which triplets count for the triplet-ordering criterion and limits it to the evaluation part. Reason: review of the labels showed that only 20 of the 50 close words are strict synonyms, so the earlier wording, "synonym < related < unrelated" over "labeled triplets", did not identify a denominator. The 90% threshold is unchanged. Made by the project owner before any Phase 2b or 2c result exists; only the Phase 2a technical checks had been run.
- **2026-11-03 (Stage B documentation; amendment 3).** Status: the design is accepted by the project owner; the B1 core composition and the B2 field rules are **not yet ratified** (Stage C). Made before Granite has been run on any curated word set: only the Phase 2a technical checks exist. **No threshold is changed.**
  1. **Scope.** Diverge is a personal portfolio project whose goal is a public web application. Evaluation with human participants is postponed, not discarded (`docs/future/human-evaluation.md`), and no criterion in this file depends on it.
  2. **Phase 2c deferred; P0 provisional.** The thresholds of section 5 are unchanged. P0 (only deterministic rules block) cannot meet the false-positive criterion for nonexistent strings (≤ 5%), because no deterministic rule blocks them. Adopting P0 is therefore a provisional product decision, not a 2c result, and must not be described as meeting these criteria. Any interface that uses P0 shows the notice in `docs/scoring.md` section 8.
  3. **B1 is split (replaces section 4.1 for B1 only).**
     - **Reason.** A lexical audit of the 50 triplets against WordNet and Wiktionary-derived data found that many `close` and `related` labels have no explicit support in a cited source or depend on the intended sense, and that the `unrelated` candidates have no verified evidence at all. The change follows from that evidence, not from any model result.
     - **B1a (criterion).** For each triplet of a curated *core*, `d(anchor, close) < d(anchor, related)`, strict; a tie is a miss. The core holds the rows with `close_relation` `synonym` or `near_synonym` whose sense is supported by a cited source with the sense confirmed by the project owner. The threshold stays at 90%, with k = (9N + 9) // 10. There is no development/evaluation partition, because no parameter is chosen with these rows. The core is expected to hold between 4 and 6 triplets; N is fixed at Stage C, before any run, and recorded in the word-set manifest. At the minimum (k = N) the Wilson 95% interval is 61.0–100% for N = 6, 56.6–100% for N = 5 and 51.0–100% for N = 4.
     - **B1b (descriptive, no threshold).** `d(anchor, related)` against `d(anchor, unrelated)` over all triplets, reported by level and labeled "`unrelated` candidates, not verified negatives". The complete order `close < related < unrelated` is also reported descriptively.
     - **B1a is less demanding than the original criterion.** It drops the `related < unrelated` inequality because the `unrelated` candidates are unverified. This is declared here and does not come from any result.
     - **Limits stated with every result.** B1a is an exploratory benchmark of a few rows, not a generalizable estimate. A definition that mentions a concept does not predict a distance: passing does not validate the relation or the model, and failing does not refute them. The core rests on **one collaborative source in Spanish, with no independent corroboration**. Granite played no part in choosing the rows, and the original labels and states are untouched.
  4. **B2.** The 95% threshold, N = 1,002 and the minimum of 952 hits are unchanged, as are the unit of observation, the hit and the independence limitation of section 4.2. What changes is how the 12 fields are populated: each word is assigned to a field from a cited source, per sense, with the root synsets and the path rules recorded for audit (`docs/phase-2b-design.md` section 8). Those rules are not ratified until Stage C. If the classification leaves a field below the working minimum of 8 words, the work stops and the situation is reported before any change.
  5. **What stays as written.** Sections 1–3, 4.2 and 6, the 2b invariance and normalization criteria, and every threshold of section 5.
