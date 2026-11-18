# Decision log

Status: 2026-11-03. D1 to D11 come from the Phase 1 plan (translated from Spanish); their current state is shown. D12 onwards were taken afterwards. Decisions made by the project owner unless stated. This file records decisions; the reasons live in the linked documents.

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included. `CLAUDE.md`, cited in some historical documents, is a private project-context file and is not part of this distribution.

## D1–D11 (Phase 1 plan)

| ID | Topic | Current state |
|---|---|---|
| D1 | Python version | **Resolved:** Python 3.12 in an independent virtual environment (`.venv` at the repository root) |
| D2 | Protocol | **Resolved:** `dat7` is official; `all10` is an exploratory own variant (`scoring.md`) |
| D3 | Strict vs permissive validation | **Superseded by D14:** P0 is adopted provisionally; Phase 2c is deferred |
| D4 | Licenses | **Resolved:** spaCy and its GPL-3.0 models excluded; wordfreq is an experimental dependency with attributions (`third-party-review.md`) |
| D5 | Deployment | **Resolved:** local first; Docker last, with a volume or cache for the model weights |
| D6 | `CLAUDE.md` edits (a private project-context file, not part of this distribution) | **Approved** and applied; amended again on 2026-11-03 |
| D7 | Git | **Approved:** `git init` before any implementation |
| D8 | Name and interface copy | **Open, low impact:** confirm "índice de divergencia semántica" and the Spanish texts. The P0 notice (D14) is fixed |
| D9 | Who labels the gold sets | **Open:** the project owner labels, with provenance recorded; no second reviewer so far. Review now rests on cited source evidence (D15) |
| D10 | Contact the S-DAT authors | **Postponed, optional:** to ask for coefficients and the 100-noun list. Does not block anything |
| D11 | Acceptance criteria for FN/FP | **Resolved:** thresholds committed before any 2c run; amended in section 7 of `acceptance-criteria-2c.md` without changing thresholds |

## Decisions after the Phase 1 plan

| ID | Date | Decision | Where |
|---|---|---|---|
| D12 | 2026-11-03 | **Project scope.** Diverge is a personal portfolio project whose goal is a public web application. It is not psychometrically validated and does not measure creativity. *Scope superseded by D21 (2026-11-06); this entry is kept as the historical record* | `CLAUDE.md` §1 |
| D13 | 2026-11-03 | **Human evaluation postponed, not discarded.** No recruiting, no distribution of the kit forms. Kit v1.2, its scripts and documents are kept. The MVP stores no participant data, profiles or tracking; any future human evaluation stays separate from the core engine. *Scope superseded by D21 (2026-11-06): a human study becomes part of the project, under the conditions of D21; this entry is kept as the historical record* | `future/human-evaluation.md` |
| D14 | 2026-11-03 | **P0 provisional; Phase 2c deferred.** P0 is a product decision, not a 2c result. 2c thresholds are unchanged. The user notice of `scoring.md` §8 is shown while P0 is active | `acceptance-criteria-2c.md` amendment 3 |
| D15 | 2026-11-03 | **Evaluation without participants.** Mathematical, technical, computational-semantic (cited, source-backed word sets), software and, later, usability checks. B1 is split into B1a (threshold 90%, curated core, no partition) and B1b (descriptive). B2 keeps 95% / 1,002 / 952 with fields classified from cited sources. **Design accepted; core composition and B2 rules not ratified** | `evaluation-strategy.md`, `phase-2b-design.md` §8 |
| D16 | 2026-11-03 | **Word-set freeze must be atomic and tested** (design only; script not yet rewritten). No v1.0 before stages B, C and D | `phase-2b-design.md` §8.6 |
| D17 | 2026-11-03 | **wordfreq-derived data stays out of Git** (`experiments/results/wordfreq_*/` ignored). Committed in `85dd35f` with the corrected docstring of `frequency_report.py`. On 2026-11-03 the aggregate statistics that `1ed5b5f` had placed in `phase-2b-design.md` were removed from the current text; history is unchanged | `third-party-review.md` |
| D18 | 2026-11-03 | **Conservation before changes.** A private backup outside the repository (Git bundles before and after the first commit, plus the files Git does not hold) was made and verified, and recovery was tested. The first commit holds six paths and no co-author trailer | `roadmap.md` stage A |
| D19 | 2026-11-03 | **Lexical adjudication policy. Ratified; implementation dependencies open.** Triplet relations are adjudicated per sense and per pair (`anchor–close`, `anchor–related`, `anchor–unrelated`), with original labels intact and B1a eligibility based on the adjudication. Full text in the section "D19" below. Thresholds unchanged | section "D19" below |
| D20 | 2026-11-04 | **Auxiliary regional inventory. Ratified by the project owner on 2026-11-04.** `experiments/wordsets/regional/` records regional lexical relations with their sources, separate from the benchmark. It does not change D19, any threshold or any word set | section "D20" below |
| D21 | 2026-11-06 | **Scope v2: local semantic analysis application and a human-similarity study. Decided by the project owner on 2026-11-06.** Replaces the product goal of D12 and the postponement of D13. The word pair is the main unit; sets of variable size yield all pairs; their mean distance is an experimental indicator; DAT7 becomes historical and optional. Granite at the pinned revision stays the reference model. The DAT line is preserved (tag `dat-line-v0.1`) and its decisions are not rewritten | section "D21" below |

## D19 · Lexical adjudication policy

**Status: ratified by the project owner on 2026-11-03. Implementation dependencies are open (section 18).** No threshold is changed by this decision, and no earlier decision is rewritten.

**1. Scope.** This policy applies to all 50 triplets before any distance is computed and before the B1a core is selected. Original CSV labels stay intact. Any discrepancy between an original label and an adjudication is recorded and explained in the evidence file.

**2. Unit of adjudication.** Adjudication is per sense. Each triplet has three independent adjudications: `anchor–close`, `anchor–related` and `anchor–unrelated`. Each pair records its own senses, evidence and relations. No overall triplet classification replaces them. A pair may have different relations in different senses, recorded separately.

**3. Three separate dimensions.**

- *Relation type:* `strict_synonymy`, `near_synonymy`, `hypernymy`, `hyponymy`, `meronymy`, `holonymy`, `co_hyponymy`, `morphological_derivation`, `semantic_association`. An abbreviation is recorded as `morphological_derivation` with the subtype `abbreviation`.
- *Evidence state:*
  - `documented`: a traceable source with explicit evidence exists and no corroboration indicator (section 9) remains pending.
  - `corroborated`: additional corroboration exists from an independent source (section 8) and the corresponding indicators are resolved.
  - `pending`: evidence has not been gathered or evaluated yet, or is insufficient.
  - `conflicting`: a same-sense contradiction exists (section 6).
  - `not_demonstrated`: no relation has been documented. It never means that no relation exists.
- *Review state:*
  - `unreviewed`: not yet examined by the adjudicator.
  - `reviewed`: examined by the adjudicator, without a decision.
  - `accepted`: the adjudicator accepts the classification for the purpose of the benchmark.
  - `rejected`: the adjudicator discards that classification, with a documented justification.

For `anchor–unrelated`, `accepted` never means that the semantic independence of the words has been demonstrated. It only means that the pair is accepted for treatment as an `unrelated` candidate after the review procedure of section 11.

`adversarial_reviewed` is a record that a review procedure was carried out. It is neither a semantic conclusion nor negative proof.

**4. What evidence can establish, by relation type.** There is no universal scale of strength. A Spanish noun entry for the exact lemma is a prerequisite and establishes no relation.

- `strict_synonymy`: requires substantial equivalence in the evaluated sense and no relevant difference in meaning. A sense-level synonym listing or an identifying definition supports it, once the concrete sense is checked. A synonym list, even a mutual one, is evidence but not automatic proof of strict interchangeability.
- `near_synonymy`: requires semantic proximity and a difference of register, scope, domain or nuance documented in a source. An `intended_sense` written by the adjudicator cannot by itself create that difference.
- `hypernymy` and `hyponymy`: a sense-level listing or a genus definition, with a clear direction. They show inclusion, not synonymy.
- `meronymy` and `holonymy`: a definition or listing that states the part–whole relation. Co-occurrence in a definition is insufficient.
- `co_hyponymy`: a taxonomic relation, recorded on its own and not as thematic association. It requires a documented shared hypernym in the relevant senses or an explicit coordinate listing. Sharing a semantic field is insufficient.
- `semantic_association`: a definition or sense-level link that connects the two words directly in the evaluated sense, without equivalence, inclusion or a part–whole relation. A `relacionado` link is only a lead until the sense has been read.
- `morphological_derivation`: etymology or a documented morphological rule. It shows form, not meaning.

WordNet and English glosses may corroborate a concept. They do not establish Spanish usage by themselves. Transitive inference and human judgment are recorded as such and do not count as source evidence. The adjudicator may fix the evaluated sense and resolve a case with stated reasons, but this does not create evidence.

**5. Absence of a link.** The absence of a lexicographic link never demonstrates the absence of a relation.

**6. Same-sense check and conflicts.** A contradiction exists only after checking that both pieces of evidence correspond to the same sense. Evidence for different senses is recorded separately and is not a contradiction. If the target sense of a listing is not stated, this is recorded and any attribution is marked as the adjudicator's. For a genuine same-sense contradiction, `relation_conflict` is recorded, both pieces of evidence are kept and the evidence state is `conflicting`. It stays unresolved while the evidence is insufficient. No relation is applied automatically, and the weaker relation is not applied by default.

**7. Plurals, derivation and grammatical headings.** Normalizing a plural may locate a lemma. The evidence counts only if it corresponds to the evaluated sense and context, and the plural is not lexicalized. Morphological derivation and plurals do not by themselves demonstrate a semantic relation. A derived pair needs independent semantic evidence, recorded separately from the derivation; a derived pair can be admissible for `anchor–related` only when such evidence exists. An adjective heading does not automatically establish noun use: a relation found under one needs a noun heading or a further source documenting noun use.

**8. Sources and independence.** One traceable source with explicit evidence can justify the state `documented`. Two sources are not independent when one reproduces or derives from the other. When a collaborative source cites an older dictionary, consulting that dictionary verifies provenance; it is not automatically a second independent corroboration. Collaborative sources are used with their revision, date, licence and a reading of the sense.

**9. Indicators that require additional corroboration.** A pair requires additional corroboration when at least one of these applies:

1. `relation_conflict`;
2. target sense not explicit;
3. use "by extension";
4. strict synonymy supported only by lists;
5. a definition that depends on historical sources (the corroboration must then be contemporary);
6. a difference of grammatical category;
7. ambiguity affecting the evaluated sense.

A pair with no indicator does not need a second source. No specific dictionary is mandatory.

**10. B1a eligibility.** Eligibility rests on the semantic adjudication, not exclusively on the original label.

- `anchor–close` must be `strict_synonymy` or `near_synonymy`.
- `anchor–related` must be a direct `semantic_association` or a part–whole relation (`meronymy` or `holonymy`) with the anchor. A link that exists only through `close` is not direct.
- The evidence state must be `documented` or `corroborated`.
- Hypernymy, hyponymy, co-hyponymy, abbreviations and derivation are excluded from the core and remain available for descriptive analysis. A derived pair qualifies as `anchor–related` only through a separately documented `semantic_association`, never through its derivation.

**11. `anchor–unrelated`.** It is never a verified negative. Review is proportional: identify the relevant senses, look for plausible relations with the anchor, record any link found, and document when the search found none. That result is not evidence of semantic independence. An exhaustive study of every possible sense is not required.

**12. Insufficient evidence.** A pair with insufficient evidence stays `pending`, is not rejected for that reason alone, and its triplet does not enter the core. It remains available for descriptive reporting.

**13. Selection bias.** Requiring documented relations favours standard, frequent, well-documented vocabulary and lexicalized relations, and may exclude regional or recent uses. Results describe the selected rows and do not estimate general model behaviour. Excluded rows and their reasons are published with the results. No row is replaced after results.

**14. Evidence and storage.** Adjudication data and evidence items are kept separate. Verbatim captures from Wiktionary and DAMER stay out of Git while their reuse conditions are unresolved. Versioned material may contain references, entry identifiers, revisions, dates, evidence types and hashes, without quotations whose treatment is unresolved. This structure does not by itself guarantee licence compliance.

**15. Status of provisional candidates (not a selection).** t08, t20, t43 and t48 are candidates under review. t28 and t37 are outside the provisional selection. The core is not selected by this decision. For t48 `carta–cartero`:

- the morphological derivation is documented;
- the definition of cartero.1, describing the person who distributes the letters of the mail, is semantic evidence of association;
- that definition refers to Labernia (1866), so independent, contemporary corroboration is pending (section 9, indicator 5);
- the evaluated sense of `carta` must be stated explicitly.

t48 stays a pending candidate, neither accepted nor rejected.

**16. Number of eligible records.** After the 50 triplets are adjudicated:

- If fewer than four records are eligible, B1a is not executable under its current design. Thresholds are not lowered, records that fail the criteria are not added, and rows are not substituted automatically. Any change to the design requires an independent methodological decision and approval before distances are computed.
- If more than six records are eligible, the selection of the core must be approved and documented before distances are computed.
- In every case the core composition is ratified before distances are computed (stage C of `roadmap.md`). This section adds conditions and changes no threshold.

**17. `review_status` of the CSV files.** This decision does not redefine the `review_status` column of the CSV files. How the three pair adjudications map to a general review state for each triplet is a pending implementation dependency of the future rewrite of `freeze_wordsets.py`. It is not resolved here by inference and the script is not changed by this decision.

**18. Open implementation dependencies.**

- Mapping from the three pair adjudications to the `review_status` value of each triplet (section 17), and the matching change in `freeze_wordsets.py`, which today reads `close_relation` (`CRITERION_RELATIONS`) and `review_status`.
- A note on the wording of amendment 3 in `acceptance-criteria-2c.md` and of section 10 of `CLAUDE.md`, which describe the B1a core by `close_relation`. Until that note is authorized, section 10 above governs eligibility and those texts are read together with it. No threshold is affected.
- The schema of the evidence file and where it lives, with verbatim captures outside Git (section 14), and their coverage by the private backup.
- Sources acceptable as contemporary independent corroboration, and whether a second reviewer will adjudicate.
- Verbatim recapture of the quotations, per-entry licences, the DAMER/RAE terms and the kaikki transfer (see "Open decisions").
- The candidate list in the "Open decisions" table (t08, t20, t37, t43, t48) predates this decision; the provisional status in section 15 is the current one.

## D20 · Auxiliary regional inventory

**Status: ratified by the project owner on 2026-11-04.** This ratifies the rules of the inventory. It adjudicates no record or correspondence: `reg-0001`, `reg-0002` and `cor-0001` stay undecided.

1. **Purpose.** `experiments/wordsets/regional/` records lexical relations of regional Spanish with their sources. It documents vocabulary and estimates nothing.
2. **Separation from the benchmark.** The inventory is not an input to B1, B2, B8, any other battery, Phase 2c or the word-set freeze. A record enters any of them only through a separate decision, made before distances are computed. `edge_cases_v0.1.csv` and its controls do not change.
3. **No extension of D19.** The inventory reuses D19 vocabularies, registries and capture conventions, and the rules of its sections 3, 4, 5, 6, 8, 9 and 14. Sections 10 and 16 do not apply. Local vocabulary extensions are defined only in the inventory's module and D19 does not admit them. This decision does not change D19 or its validator.
4. **Independent evaluation of claims.** Each record is evaluated claim by claim: the source sense, the published target sense, the relation between them, the regional attribution and, for `near_synonymy`, the difference. Provenance and independence are recorded for each evidence item. An item supports only the claims it declares in `supports_claims`, and a person checks that the source really contains them. A source that defines a word does not thereby show synonymy, and a word that appears in a gloss, or a compatible definition, does not show a relation. A regional mark is a lexicographic attribution, not proof of usage.
5. **Aggregation of evidence.** Different sources of one record may cover different claims, and each keeps its provenance and function: no claim is credited to a source that does not declare it. Items of another record never count. A usage attestation never becomes a lexicographic attribution, however many there are.
6. **Reference correspondences.** Whether two lexicographic references name one sense is decided apart, in `reference_correspondences_v0.1.csv`, whatever the state of the record, so it may be decided while the record stays `pending`. A cell of the inventory holds one reference. Only an `accepted` correspondence connects two references; it needs a registered human adjudicator, a date and a rationale. A proposed (`unreviewed`), `reviewed` or `rejected` correspondence connects nothing. Correspondences are not chained.
7. **Correspondence is not a lexical relation.** An accepted correspondence resolves the identity of references. It does not show synonymy or any relation between the words, creates no evidence, does not raise an evidence state and is never shown as an accepted relation. Once it is accepted, the item that declares the relation stays its only source.
8. **Internal glosses.** `gloss:` labels and `sense_b` are representations of working concepts of the project, not published lexicographic senses. A `gloss:` label may appear only in `sense_b_ref`. It does not count for `target_sense_explicit`, `target_sense_delimited`, `documented` or `corroborated`, accredits no relation or difference, cannot be part of a correspondence and is never a source or independent evidence. A paraphrase compatible with both words does not complete a relation.
9. **Published senses.** A target sense is delimited when a lexicographic item with a verified capture identifies a published sense explicitly (by number, or because the target has one sense in that category in the source) and starts from a source sense of the record, or is the entry of that target sense. This is checked separately from regional coverage. A published target reached from another source reference stays complementary until a correspondence is accepted. A reference in a record that has not been accepted is a proposal.
10. **`documented` and `corroborated`.** `documented` needs the relation type, both senses and their published references, coverage of the source sense, the target sense, the relation and the regional attribution by items with verified captures, no pending indicator and, for `near_synonymy`, an accrediting difference item. `corroborated` also needs two sources that each cover the same complete claim with their own attribution, at least one recorded as independent, with no derivation between them. Informal sources, derived sources and marks of unknown provenance do not count for it. A single item covering everything is a descriptive fact, not a requirement and not a validation.
11. **Provenance of marks.** A mark is recorded as the source's own only when that origin is established. A derived mark records provenance and dependencies only and never counts. A mark unbacked by the cited source does not count. In an institutional or historical dictionary, with an explicit mark in a traceable entry, a mark of unknown provenance may support `documented` as a traceable lexicographic attribution, not as evidence of general usage; it is never presented as the source's own or as independent and never supports `corroborated`. Collaborative sources cannot use this. A source that does not mark a variety does not contradict one that does. The general scope of a work is recorded in `source_scope`, and the individual mark of a sense in `region_signal`. They are different dimensions and neither replaces the other: a work with the scope of a variety, such as the DAE, may include shared words with no individual mark. Its scope implies neither exclusivity nor origin, is not a regional attribution and changes no requirement of `documented` or `corroborated`. Examples reproduced by a dictionary are not separate or independent sources.
12. **Conflicts.** `relation_conflict` concerns the relation between two published senses and needs lexicographic, non-derived items that support and contradict it; human judgment and usage items are not grounds. `region_conflict` is a local indicator for an explicit exclusion of the variety opposed to the source's own attribution or to an attribution of unknown provenance, for the same sense, and both items must be lexicographic, non-derived and non-collaborative. Derived or unbacked marks are not grounds, and the absence of a mark never produces either conflict. The local set of pending indicators adds `region_conflict` to the D19 indicators without changing them.
13. **Near synonymy.** Evidence of the relation is distinct from evidence of the difference that justifies `near_synonymy`, which may come from the same item or another. A candidate item identifies a possible difference and may keep a proposal in a pending record; it does not accredit it. An accrediting item explicitly supports both senses and the specific kind of difference. The validator checks structure and references; whether the source really compares both senses is for human review. A definition that adds a restriction does not by itself show a difference fit for `near_synonymy`: the adjudicator determines whether the source really documents a difference of scope, register, domain or nuance. A register mark on one word, an adjudicator's inference, an informal source or developer confirmation cannot create a difference. Without it, `relation_type` stays empty or a proposal, the record stays `pending` and it never becomes `strict_synonymy` automatically.
14. **Historical sources.** The nature of a work, the period of its documentation and the dependence of a definition on historical sources are recorded separately. Dependence keeps its D19 meaning, is not inferred from a work's type or from dates, and is recorded as unknown when not established. No time threshold is defined.
15. **Adjudication states.** `unreviewed` is a proposal. `reviewed` is an examination without a decision. `accepted` and `rejected` are decisions of a registered human adjudicator, with a date and a rationale. Records and correspondences are adjudicated separately. Resolving an indicator needs an `accepted` or `rejected` decision on the record. An accepted record needs `documented` or `corroborated`; an accepted correspondence does not. Evidence state, human review and developer confirmation are independent: confirmation is an explicit statement of the project owner about usage, recorded only in its own fields; it is not a lexicographic source or independent evidence, never raises an evidence state and never implies acceptance, and a `documented` record stays unaccepted until a registered adjudicator accepts it.
16. **Versioning and third-party material.** Versioned in Git: the record, evidence and correspondence tables, bibliographic references, normalized factual annotations such as `region_signal` and `register`, the validator, its tests and the documentation. Kept outside the repository: captures of sources, transcriptions and long excerpts, copies of original documents, and material whose licence needs review. The normalized annotations are project data derived from the sources, not reproductions of their definitions. This is a handling rule, not a finding on licence terms; the DAMER and RAE terms remain unresolved.
17. **Pending records.** Being pending is never an error. Validation separates structural validity, evidence sufficiency, consistency of a proposal and human adjudication. A structurally valid record may stay pending or unreviewed, and such records block no benchmark step.
18. **Limits of the validator.** The validator only reads. It never writes, changes, adjudicates or resolves a relation, a correspondence or a state. A valid structure is not semantic correctness.

## D21 · Scope v2: semantic analysis of Spanish words

**Status: decided by the project owner on 2026-11-06.** It replaces the product goal of D12 and the postponement of human evaluation in D13. D1 to D20 keep their text. Where they describe the DAT-inspired product, they now describe the preserved DAT line, not the current product.

**1. Product.** Diverge is a local application for analyzing semantic similarity and divergence between Spanish words with multilingual embedding models run locally. The user enters words; the application computes their embeddings and their semantic distances and presents them understandably. Priorities:

- Local inference, with no external service needed to compute embeddings.
- Separation between the semantic engine, the API and the interface. The engine is usable without FastAPI.
- Reproducible processing.
- Identification of the model version and of its configuration in every result.
- Input validation and explicit error handling.
- Transparency about what results mean and their limits.

**2. Research.** The project studies how far the model's distances correspond to human ratings of semantic similarity given by speakers of Ecuadorian Spanish.

- **Provisional question:** *«¿En qué medida las distancias semánticas calculadas por un modelo de embeddings multilingüe se corresponden con las valoraciones humanas de similitud semántica de hablantes de español ecuatoriano?»* (How far do semantic distances computed by a multilingual embedding model correspond to human ratings of semantic similarity by speakers of Ecuadorian Spanish?)
- **Provisional construct:** semantic similarity, kept distinct from association or contextual relatedness.
- **Not a validation.** This is an evaluation of the model against human judgments. It is not a psychometric validation of any instrument.

**3. Unit of analysis.**

- **Pairs.** The word pair is the main unit. Its distance is `d = 1 − cos(e_a, e_b)`, in [0, 2], and its similarity is `cos(e_a, e_b)`.
- **Sets.** A set may hold a variable number n of words and yields all N = n(n − 1) / 2 pairs.
- **Mean distance.** It may be kept as an **experimental indicator** of a set. It is never presented as a validated measure of creativity.
- **DAT7.** The protocol (first seven eligible words, 21 pairs, mean × 100; `scoring.md` §1) becomes a historical reference and an optional function. It is not the center of the product and does not condition its architecture.

**4. Reference model.**

- `ibm-granite/granite-embedding-278m-multilingual`, revision `a9cb5338491faf32b73dd17b714a31821c021bbf`.
- **Documented configuration:** CPU, fp32, 768 dimensions, CLS pooling followed by one L2 normalization (`Normalize` module), sdpa attention, offline.
- **How the DAT7 baseline encoded,** verified in `experiments/results/semantic_baseline_dat7_v0.1/run_baseline.py`: one call per set with its seven words in entry order, `batch_size = 32`, so a single batch; the cosine computed in float64 with no clipping.
- **No claim beyond reproducibility.** Passing reproducibility checks does not show the model is the best for Spanish, nor that it is semantically validated.

**5. Levels of evidence.** Three levels are kept apart:

1. **Mathematical consistency:** reproducibility of the calculation and software tests (E0).
2. **Correspondence with human similarity judgments:** level **H1**, new. Evidence about how model distances relate to human similarity ratings. It is not validity of creativity and is distinct from E0 to E3.
3. **Psychometric validity:** whether a tool measures creativity or another psychological construct (the E3 of the DAT line). **Out of scope.**

**6. What Diverge does not claim.** It does not measure individual creativity, intelligence, originality or cognitive abilities. It is not a validated psychometric instrument. It does not reproduce the scientific validity of the DAT. It does not transfer DAT norms, percentiles or baremos. It is not presented as the first multilingual system for semantic-divergence analysis.

**7. Human data.**

- Participant data never passes through the engine or the API.
- Ratings are handled anonymously and kept outside the repository.
- No human data is collected before the study design and the applicable institutional requirements are complete.

**8. Preservation.** The DAT line stays recoverable as earlier research:

- Annotated tag `dat-line-v0.1` on `c7a76d0`.
- Bundle `pre-scope-v2.bundle` and payload `pre-scope-v2-payload.zip`, both verified; verified copies exist in a private backup that is not part of this distribution.
- Its documents are kept as written, including statements that described the state of that time: `spec_2b.json`, `validate_spec.py`, `phase-2b-design.md`, `acceptance-criteria-2c.md`, the curated word sets, the DAT results and the B2/B3/B4 proposals.
- D19 and D20 are unchanged.

**9. What D21 does not change.** The distance formula, the normalization (`strip`, NFC, `casefold`, NFC), the reference model and revision, the tolerances, D19, D20, and every threshold of the DAT line.

**10. Pending, to be resolved in their stages with technical or methodological justification.**

- Maximum number of words per set.
- Processing policy above 32 words.
- Final treatment of batches with several pairs.
- Presentation scale of the set indicator: the DAT-line index multiplies the mean by 100.
- Final format of the human rating scale.
- Number of raters and of pairs.
- Final statistical method.
- Final consent protocol.
- The concrete institutional procedure.

## Open decisions (none is taken until the project owner answers)

Rows marked "Current decision" record a decision the project owner has already taken; what stays open is stated in the row itself.

| Topic | What is needed | Stage |
|---|---|---|
| t28 (comida ~ cocina) | Which sense was intended: place or activity. Without confirmation it stays out of the B1 core | C |
| B1 core composition | Ratify the core after verbatim recapture of every quotation (t08, t20, t37, t43; t48 conditional) | C |
| B2 field rules | Roots, tag lists, the "first listed nominal sense" convention, `confirmed` by declared ILI | C |
| kaikki transfer | Authorization to stream `es-extract.jsonl.gz` (103,226,090 bytes) and keep only a filtered subset outside the repository | C |
| History of `1ed5b5f` | Whether to rewrite history to remove wordfreq-derived aggregates. Not done; not authorized. This history belongs to the private research repository and is not part of the current public distribution | I |
| Repository license | **Current decision (2026-11-18):** Diverge is prepared for public distribution without a license of its own. No general license is granted for its original material, and this decision does not authorize the general reuse of that material. Apache-2.0 remains a possible future option. Still open: a future license, and how definitions from third-party sources are treated | I |
| DAMER / RAE terms | Read the legal notice manually; decide the use of marks. `edge_cases_v0.1.csv` stays untracked meanwhile | I |
