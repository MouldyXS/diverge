# Phase 2b design: semantic behavior (DRAFT)

Status: draft for review, 2026-11-03; **amended 2026-11-03 (section 8: B1 is split into B1a/B1b, B2 fields come from cited sources, word sets are reviewed by source evidence)**. Thresholds come from `acceptance-criteria-2c.md` section 4 and are not changed here. All results are **experimental criteria (E1–E2), not validation**. Labels: **FACT**, **PROPOSAL**, **UNCERTAIN**.

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included.

## 1. Question

Does the stack verified in Phase 2a (`experiments/results/2a_20261103_004339/manifest.json`) produce distances that behave plausibly for Spanish single words, and how stable is the index? Phase 2b does not use wordfreq and does not choose a validation policy.

## 2. Word sets (`experiments/wordsets/curated/`, version 0.1)

All rows are **drafts written by the assistant**. They are not labels until the developer reviews them (decision D9), which changes `review_status`. Since the amendment of section 8, that review rests on cited source evidence, not on human participants.

| File | Content | Use |
|---|---|---|
| `triplets_v0.1.csv` | 50 triplets: anchor, close word with its relation and intended sense, related, unrelated | Triplet ordering |
| `nouns_v0.1.csv` | 12 semantic fields of 15 words, plus a `general` list | Single-field and mixed-field sets; random baseline pool |
| `diverse_sets_v0.1.csv` | 12 hand-built diverse sets and 2 opposite-based sets, 10 ordered words each | Upper-range and low-range examples; `dat7` vs `all10` |
| `edge_cases_v0.1.csv` | Word pairs: antonyms, polysemy, plurals, missing accents, diacritic pairs, typos, loanwords, regional equivalents, nonsense | Descriptive report; no pass/fail threshold except diacritic pairs |

**Regional rows.** Geographic exclusivity is not required. Each row records one sense, the places where that sense is documented (`region`, DAMER marks as printed, because ISO codes cannot express marks such as `Ar:NO`), whether its use in Ecuador was confirmed by the developer (`ec_use`), and the source consulted (`label_source`). Canguil, chuchaqui, guagua, ñaño, chompa, poroto, funda, chamba and vereda are kept as valid candidates of Ecuadorian use by the developer's decision. DAMER was read through an automatic text extractor; Córdova Malo was not consulted. Three rows (`computadora`, `carro`, `celular`) were not checked against any source. These rows exist for inspection in 2b and do not replace the labeled F4 set of Phase 2c.

**Triplet relations.** The close word is not always a strict synonym, so each triplet records `close_relation` and, where needed, `intended_sense`:

| Relation | Triplets | Examples |
|---|---|---|
| `synonym` | 20 | coche/automóvil, idioma/lengua (language system, not the organ) |
| `near_synonym` | 17 | anciano/viejo (noun; register differs), trabajo/empleo |
| `anchor_is_kind_of_close` | 6 | guerra/conflicto, barco/embarcación |
| `close_is_kind_of_anchor` | 4 | dinero/efectivo, cuchillo/navaja |
| `abbreviation` | 2 | bicicleta/bici |
| `part_or_unit` | 1 | libro/tomo |

**Freeze rule (current script; to be rewritten in Stage D, section 8):** `experiments/wordsets/freeze_wordsets.py` refuses to freeze until every triplet and regional row is marked `reviewed` or `rejected`. It then writes the `v1.0` files, their hashes and the split to `experiments/wordsets/manifests/wordsets_v1.0.json`, all committed **before the first 2b run**. Rejected rows are listed in the manifest, not dropped silently.

## 3. Partition

Decisions use the development part only. The evaluation part is run once, after the decisions are frozen, and every figure is labeled with its partition. The split uses seed `20261102` and is stored explicitly in the manifest, because NumPy does not guarantee the same random stream across versions.

| Data | Split unit | Why |
|---|---|---|
| Triplets | Whole triplet, within each relation (original design; B1a uses no partition, section 8) | Anchors are unique, no word repeats across triplets, and both sides keep the same mix of relations. |
| Noun fields | **Whole field**, 6/6 | See below. |
| General nouns | Word, 61/61 | No field structure to preserve. |
| Diverse and opposite sets | Whole set, within each kind | Sets are used as units. |
| Edge cases | Not split | Descriptive only; no decision may be taken from them. |

**Why whole fields (PROPOSAL):** splitting each field's 15 words in half would leave 7 or 8 words per field, so a single-field set of 7 would have at most 8 distinct versions. Splitting by field keeps C(15,7) = 6,435 possible sets per field and evaluates on fields not seen during decisions. The cost is that each part has six fields, so mixed-field sets use one word from each of the six fields plus one general noun, and results depend on which fields fall on each side. The between-field matrix makes that visible.

The only decision taken in 2b is the input format. Rule (PROPOSAL): keep the bare word unless a template gets **at least 3 more triplets correct, net**, on the development triplets of the B1 denominator. The rule is an absolute count because proportions depend on the sample: 3 triplets are 6% of 50, but the decision uses only the 18 development triplets of that denominator (3/18 = 16.7%). It is a practical minimum, not a statistical test: three discordant triplets in the same direction give an exact McNemar p of 0.25. That is why the bare word is the default. A template shifts all distances, so raw index values are not compared across formats. Candidate template: `palabra: {word}`.

**Link with Phase 2c (PROPOSAL):** any word inspected in `edge_cases` during 2b may enter the 2c labeled sets only on the development side, and the nonsense strings used here are not reused in the 2c evaluation part. Thresholds in `acceptance-criteria-2c.md` do not change.

## 3.1 Sampling

The pool file keeps its original distribution (12 fields of 15 words, plus 122 general nouns). Words are never removed or duplicated to balance it; balance comes only from the sampling weights, which are recorded in each run's manifest.

- **Primary baseline: stratified.** For each word, draw a stratum with equal weight, then a word uniformly within it, without repeating a word in the set.
- **Sensitivity: uniform over words.** Reported next to the primary baseline to show how much the reference depends on this choice.

**Strata and weights.** The pool has **13 strata**: 12 fields and the general list. Fields are **never grouped**. The seven strata used in each run come from the partition, not from merging fields: each part holds 6 whole fields plus its half of the general list.

| Scope | Strata | General share, stratified | General share, uniform | Probability of one field word vs one general noun |
|---|---|---|---|---|
| One part (development or evaluation) | 7 (6 fields + general) | 1/7 ≈ 14.3% | 61/151 ≈ 40.4% | 61/15 ≈ 4.1 times |
| Full pool | 13 (12 fields + general) | 1/13 ≈ 7.7% | 122/302 ≈ 40.4% | 122/15 ≈ 8.1 times |

Runs that support decisions or evaluation are per part. A full-pool figure, if reported, is descriptive and produced only after the evaluation is complete. These are per-draw weights; not repeating a word within a set changes them slightly.

## 3.3 Frequency control

No word is removed because of its frequency, and `lijadora`, `azada` and `cincel` stay in the pool. The original sets remain the basis of the criteria. To control for lexical rarity, B10 repeats the comparison with frequency-matched subsets.

- **Band (a design parameter of this project):** Zipf in [3.2, 4.6), in steps of 0.1. It was chosen from wordfreq values before the model was ever run on these sets. The counts of words per field that informed the choice are not versioned: `frequency_report.py` regenerates them locally (section 3.2).
- **Known weakness:** a field with few words in the band yields few distinct single-field sets. Each B10 run must state the per-field counts it used; where they come from wordfreq they go to the ignored local results, not to a versioned file.
- **Second control:** Spearman correlation between the index and the mean Zipf of each set, on the baseline sets.

## 3.2 Frequency record

`experiments/wordsets/frequency_report.py` records the wordfreq Zipf frequency of each word, with and without accents. It is **descriptive only**: never an acceptance criterion in 2b, and Zipf 0 means "unknown to the resource", not invalid. Per-word values, the review sheet and the aggregate manifest stay under `experiments/results/wordfreq_v<version>/`, which Git ignores: wordfreq data and everything derived from it stay out of the repository. (Earlier versions of sections 3.3 and 6 carried wordfreq-derived aggregates; they were removed from the current text on 2026-11-03 and remain in history; see section 8.7.)

wordfreq is pinned to 3.1.1 in `experiments/requirements-experiments.txt`. The report refuses to run with another version, and the version is recorded in the review sheet, the report manifest, the word-set manifest and each run manifest.

## 4. Batteries

| # | Battery | Method | Criterion |
|---|---|---|---|
| B1 (original wording; replaced by B1a/B1b, section 8) | Triplet ordering | d(anchor, close) < d(anchor, related) < d(anchor, unrelated), strict. Denominator: `synonym` + `near_synonym`. The other 13 triplets are reported by relation, outside the criterion | ≥ 90% on the **evaluation part only**: at least 18 of 19 (`acceptance-criteria-2c.md` section 4.1) |
| B2 | Single-field vs mixed-field | Pairs (S, M) within a part: S = 7 words of one field; M = one word from each of the part's six fields plus one general noun, with no word shared with S. Evaluation: 6 fields × 167 = 1,002 pairs. Development: same procedure on development fields, for debugging only | ≥ 95% on the **evaluation part only**: at least 952 of 1,002 (`acceptance-criteria-2c.md` section 4.2) |
| B3 | Invariance | Permuted order, NFC vs NFD input, upper/lower case, on 200 seeded sets | index differs by < 1e-6 |
| B4 | Normalization | The six diacritic pairs | distinct after normalization, both embedded, nonzero distance |
| B5 | Distribution | Histogram of pair distances; index over 10,000 seeded sets of 7, stratified and uniform (section 3.1); empirical minimum and maximum; between-field matrix | Reported; flag if SD of the stratified baseline < 1 point |
| B6 | `dat7` vs `all10` | On 1,000 seeded stratified sets of 10: Spearman, absolute difference, bootstrap interval | Reported |
| B7 | Entry order and substitution | Index when words 1–7 are reordered among the 10; index when word k is invalid and word 8 enters | Reported |
| B8 | Edge cases | Distances per `kind` in `edge_cases` | Reported |
| B9 | Nonsense effect | Replace one word by a nonsense string in the diverse sets; change in the index, in baseline SD units | Reported here; judged in 2c |
| B10 | Frequency control | B2 and B5 repeated on the frequency-matched subsets; Spearman of index vs mean Zipf (section 3.3) | Reported; the B2 criterion applies to the original sets only |

**Reference values:** the baseline depends on the pool and on the sampling weights. It is reported as "model reference over pool v1.0", never as a population norm.

**Field overlap (UNCERTAIN):** the mixed-field comparison assumes the fields are distinct; `emociones`, `cuerpo` and others may be closer than expected. B5 reports the between-field distance matrix to make this visible.

## 4.1 Reporting rules

- **Criteria are fixed before results.** The thresholds of 2b and 2c are not changed after observing results. Any later change needs a new commit with a written reason, and results obtained before it are marked as obtained under the earlier criteria.
- **Absolute numbers.** Every proportion is given as k/N, for example 18/19, never as a percentage alone.
- **Confidence intervals.** Every proportion carries a Wilson 95% interval, presented as a descriptive reference under an independence assumption that does not hold exactly here (B2 pairs reuse words; B1 triplets are few), not as conclusive evidence. Differences between formats also report discordant pairs and the exact McNemar p.
- **Sample limits are stated with each result.**

- **Results by part and subcategory.** Development and evaluation are never combined. Each part reports the criterion result and each relation separately.

| Criterion sample | N | Minimum correct | Wilson 95% at that minimum |
|---|---|---|---|
| Evaluation, `synonym` + `near_synonym` (10 + 9) | 19 | 18 (18/19 = 94.7%) | 75.4%–99.1% |

| Criterion sample (B2) | N | Minimum correct | Wilson 95% at that minimum |
|---|---|---|---|
| Evaluation, 6 fields × 167 pairs | 1,002 | 952 (952/1,002 = 95.01%) | 93.5%–96.2% |

The B2 size is a balance choice (exactly 167 pairs per evaluation field, 6 × 167 = 1,002), not a power calculation. The 1,002 pairs are not 1,002 independent observations: they reuse the same 15 words per field and the same general nouns. The interval is therefore a descriptive reference under an independence assumption, not conclusive statistical evidence, and per-field results are always reported next to the pooled one. For B1, a pass at the minimum is compatible with a true rate near 75%, and the report says so. These sizes assume no triplet is rejected or relabeled in review; otherwise the minimum is recalculated at freeze and recorded in the manifest.

## 5. Outputs

`experiments/poc_semantic_engine.py` writes to `experiments/results/2b_<timestamp>/`: `manifest.json` and `summary.md` (versioned) plus CSV tables and plots (ignored by Git). The manifest includes library versions, model revision, device, attention implementation, seeds, word-set hashes and the Git commit.

## 6. Limitations of the word sets

- **Not representative of Spanish.** The 302-noun pool is an experimental reference set for this model. It is not a sample of the Spanish lexicon or of what participants would write.
- **Selection by judgment.** Words were chosen by hand, with concrete nouns over-represented in the fields. "Common" was not measured when they were selected.
- **Limited review.** The developer reviews triplets and regional rows. The nouns, diverse sets and other edge cases stay as assistant drafts unless reviewed. There is no second reviewer so far, and the labels reflect one reviewer's dialect.
- **Frequency differs between fields.** The pool keeps differences in lexical frequency between fields, measured locally with `frequency_report.py` (the values are not versioned, section 3.2). B10 reports their effect instead of hiding it.
- **Regional coverage is illustrative.** Eighteen regional rows inspect behavior; they do not measure coverage of any variety.
- **Small evaluation parts.** 19 criterion triplets in evaluation and 18 in development give wide intervals (section 4.1), and six fields per part make results sensitive to which fields fall on each side.
- **Baseline is conditional.** It depends on the pool, the weights and the seeds. It cannot support percentiles or population claims.
- **wordfreq is dated.** Its snapshot ends around 2021 and it is no longer updated, so low Zipf values do not mean a word is rare or invalid today.

## 7. What a failure means

- B3 or B4 failing is a defect in our code and blocks progress.
- B1 or B2 failing does not invalidate Granite on its own. It triggers inspection of the failing rows (draft labels may be wrong) before any decision. Changing a label after seeing results must be recorded with its reason and reported.
- Passing B1 and B2 is plausibility only. It says nothing about creativity (E3 is not claimed).

## 8. Amendments of 2026-11-03 (documentation only; no experiment has been run)

Thresholds are unchanged. See `acceptance-criteria-2c.md`, section 7 (amendment 3). Labels: **FACT** (observed in a file or tool), **PROPOSAL** (design, not ratified), **UNCERTAIN**.

### 8.1 Scope

Diverge is a personal portfolio project aimed at a public web application. Evaluation with human participants is postponed (`future/human-evaluation.md`). The batteries below use computation, software tests and cited lexical sources only. Granite has not been run on the curated word sets.

### 8.2 Why the word sets are reviewed by source evidence

A lexical audit of the 50 triplets (WordNet through the Open Multilingual Wordnet, and Wiktionary-derived data) found that many `close` and `related` labels have no explicit support in those sources or depend on the intended sense. **FACT:** `omw-es:2.0` holds no semantic relations, so every hierarchy path in the earlier audits came from `omw-en:2.0` through the shared interlingual index (ILI). Audit defects and their scope are listed in `experiments/results/lexical_audit_v0.1/ERRATA.md` (local, not versioned). The earlier audits are kept as history, not as final evidence.

### 8.3 B1a and B1b (replace B1)

| Result | Compares | Rows | Threshold |
|---|---|---|---|
| **B1a** | `d(anchor, close) < d(anchor, related)`, strict | Core only | **90%**, k = (9N + 9) // 10 |
| **B1b** | `d(anchor, related)` vs `d(anchor, unrelated)` | All rows, by relation level | None. "`unrelated` candidates, not verified negatives" |
| Full order | Both inequalities | All rows | None; descriptive continuity |

- **Core (PROPOSAL, not ratified).** Rows whose `close_relation` is `synonym` or `near_synonym` and whose sense is supported by a cited source: t08, t20, t37 and t43, plus t48 if its quotation is recaptured verbatim. t28 is undecided: the evidence supports the "place" sense, and the intended sense is not recorded, so it stays out unless the project owner confirms it. t19 and t27 are exploratory. t16 has no support and is excluded (see the errata). Every quotation is recaptured verbatim, with URL and date or revision, before the core is ratified.
- **N and the 90% rule.** For N = 6, 5, 4 the rule needs N/N, with Wilson 95% intervals of 61.0–100%, 56.6–100% and 51.0–100%.
- **Limits.** A few rows; exploratory; not a generalizable estimate. A definition that mentions a concept does not predict a distance. The core rests on one collaborative source in Spanish with no independent corroboration. There is no partition because no parameter is chosen with these rows.

### 8.4 B2 field classification (PROPOSAL, not ratified)

The 95% threshold, N = 1,002 and the minimum of 952 hits stay. The 1,002 comparisons are not independent. The classification of each noun into its field is made per sense, from a cited Spanish source, and recorded for audit:

- **Record per sense.** Spanish sense and definition (verbatim, with URL and snapshot), Spanish synset, the English synset reached through a declared ILI (`crosswalk_status` must be `confirmed` for a sense to be `supported`), the field and its root, the hypernym path, `path_length` (edges; 0 if the synset is the root), `n_paths` (distinct minimal paths to the selected root), excluded roots reached, and the decision with its reason.
- **Hierarchy.** `hypernym` relations only (not `instance_hypernym`), from `omw-en:2.0` through the declared ILI. Shortest path to a root; ties go to the lexicographically smaller id. The noun graph (82,115 synsets) is acyclic; the validator re-checks this and stops on a cycle.
- **Lookup.** Exact lemma match with `normalizer=None`, `lemmatizer=None`, `search_all_forms=False`. **FACT:** the default `wn` normalizer strips diacritics and case (`ano` also returns the senses of `año`), and `omw-es:2.0` has no `<Form>` elements, so inflected forms cannot be detected from it.
- **`general` list.** A word qualifies only if its first listed nominal sense in the Spanish source does not hang from a field root. "First listed" is an editorial convention, not a frequency claim.
- **Fields.** 12 fields with root synsets and excluded roots (for example `naturaleza` excludes artifacts, animals, persons, body parts and food). `hogar`, `naturaleza` and `musica` are heterogeneous; B5 makes that visible.
- **UNCERTAIN.** Equivalence of `omw-es:2.0` with MCR 3.0; how the Spanish Wiktionary extraction marks inflected forms.

### 8.5 Dependent batteries

B5 (distribution, between-field matrix) and B10 (frequency control) depend on the B2 classification and cannot run before it. B3, B4, B6, B7, B8 and B9 depend only on the calculation and the normalization. B4 keeps the six diacritic pairs and the tolerance d < 1e-6, fixed before any run; d ≥ 1e-6 shows only that the vectors differ.

### 8.6 Freeze script (Stage D)

`freeze_wordsets.py` will be rewritten and tested before any v1.0. Requirements: atomic publication (build in a temporary directory on the same volume, publish by renaming the directory), no automatic deletion of abandoned directories, rejection when the B1 core is not ratified, when a field has fewer than 8 words or when an id is missing, unchanged field split (compared by hash), and recomputation of the minima for N = 4, 5, 6 and for B2 = 1,002 / 952. No v1.0 exists, and none is created before Stages B, C and D are done.

### 8.7 wordfreq-derived values

Everything derived from wordfreq stays out of Git (`experiments/results/wordfreq_*/` is ignored), as decision D17 (`docs/decisions.md`) records.

- **FACT:** an earlier version of this document included five aggregate statistics derived from wordfreq 3.1.1; they were removed from this edition and are not reproduced here.
- **Resolution (2026-11-03):** those statistics were removed from the current text. The justification of the band is now regenerated locally. The band bounds stay as a design parameter of this project (see `third-party-review.md` for the classification).
- **Not done:** the history of the private research repository is not rewritten, so it still contains them, and no legal conclusion is drawn here. Rewriting needs the project owner's explicit authorization.
