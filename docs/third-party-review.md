# Third-party material review

Status: 2026-11-03, updated 2026-11-18. **This is a record of what was checked and what is pending, not legal advice.** Each resource keeps its own license and notices. The current public distribution is published without a license of its own for its original material (`NOTICE`); that does not change the obligations attached to third-party material, which stay independent. `NOTICE` and `THIRD_PARTY_NOTICES.md` exist and record those attributions.

> **Note on this distribution.** The word sets, evidence tables, regional inventory, captures and wordfreq outputs named below (under `experiments/wordsets/` and `experiments/results/`) belong to the private research repository and are not part of this distribution. The rules below describe how that repository handles them.

## Resources

| Resource | Used for | Checked | Pending |
|---|---|---|---|
| Granite Embedding 278M Multilingual (IBM) | Embeddings | Apache-2.0 (model card). MS-MARCO excluded from its training because of a non-commercial license | Recorded in `THIRD_PARTY_NOTICES.md` (2026-11-18) |
| Multilingual Central Repository (`omw-es:2.0`) | Spanish lemmas, synset assignment, Spanish definitions | CC BY 3.0 (the package `LICENSE`) | Equivalence of `omw-es:2.0` with MCR 3.0 is not confirmed |
| Princeton WordNet (`omw-en:2.0`) | Hierarchy and relations (`omw-es:2.0` has none) | License 3.0 in the package: notice and disclaimer must accompany all copies | Text on the project site (returned HTTP 403) |
| Wiktionary (Spanish edition) | Spanish definitions and sense labels | Footers of the entries `cartero` and `veneno` state CC BY-SA 4.0; Wikimedia terms | **Each cited entry**, and text imported verbatim |
| kaikki.org extraction | Machine-readable Wiktionary | Refers to the Wiktionary licenses; no license of its own is assumed | Attribution; the file has not been transferred |
| wordfreq 3.1.1 | Frequency (descriptive only) | Code Apache-2.0; some data under CC BY-SA 4.0 (README) | ShareAlike reading; sources without a stated license. Data and derivatives stay out of Git |
| DAMER (ASALE / RAE) | Regional marks for `edge_cases` | Read through an automatic text extractor | **Unresolved:** legal notice not read (HTTP 403). Marks as printed stay out of the repository; for normalized annotations see "Regional inventory" below |
| *Diccionario académico de ecuatorianismos* (DAE), Academia Ecuatoriana de la Lengua, first edition, 2023. [Official PDF](https://www.academiaecuatorianadelalengua.org/wp-content/uploads/2025/04/web_Diccionario-academico-de-ecuatorianismos-2023.pdf) | Regional inventory, `rev-0014` and `rev-0015` | Printed page 204 read in the official PDF | **Reuse conditions pending review** |
| Córdova Malo, *El habla del Ecuador* (USFQ Press, 2019) | Reference for Ecuadorian use | Not consulted | — |
| spaCy Spanish models | — | GPL-3.0; **excluded** from the MVP | — |

## Handling rules in force

- `es_definition` fields contain CC BY-SA text; files holding them stay out of the public repository until that is decided.
- Output derived from wordfreq goes to `experiments/results/wordfreq_*/`, which Git ignores; no wordfreq data is included in any public Docker image until the conditions are reviewed.
- `experiments/wordsets/curated/edge_cases_v0.1.csv` (DAMER marks) is not tracked.
- `experiments/wordsets/regional/` (decision D20) holds normalized values and references only: no definitions, excerpts or marks as printed, which stay in `experiments/results/regional_inventory_local/captures/`, ignored by Git. This does not resolve the DAMER/RAE terms.

## Regional inventory: versioning policy (decision D20)

This policy applies only to `experiments/wordsets/regional/` and its local captures. It does not change the treatment of other files.

| Class | Examples | Policy |
|---|---|---|
| Captures and copies of original pages and documents | Fetched pages and PDFs | Outside the repository |
| Transcriptions and long excerpts of sources | `captures/rev-NNNN.txt` | Outside the repository, ignored by Git, with a private backup |
| Literal quotations | Definitions, glosses, marks and country lists as printed | Only in those captures; not in versioned files |
| Material whose licence needs review | Anything not classified here | Outside the repository until it is reviewed |
| Bibliographic references | Source identifier, URL, entry and sense reference, revision, date, capture hash | Versioned, following the D19 convention |
| Normalized factual annotations | `region_signal`, `register`, `variety`, evidence and review states, correspondences | Versioned |
| Project files | Record, evidence and correspondence tables, validator, tests, documentation | Versioned |

The normalized annotations are project data derived from the sources; they are not reproductions of their definitions. They do state what a source records, for example that it marks a variety. **This policy gives no assurance of legal authorization:** the reuse conditions of DAMER, DLE, DHLE and the DAE stay unresolved. The automatic checks cover format only, so paraphrases need a human reading before any version is made.

**DAE material in the regional inventory:**

| Material | Where it stays |
|---|---|
| Bibliographic references and metadata (work, edition, URL, page, entry, `source_scope`) | Versioned |
| Own-words paraphrases in `note` | Versioned; a person reads them before any version is made |
| Definitions and examples of the work | Not in versioned files |
| Local captures and excerpts (`rev-0014`, `rev-0015`) | Outside the repository, ignored by Git, with a private backup |

## wordfreq-derived values in versioned documents (reviewed 2026-11-03)

Rule in force (decision D17, `docs/decisions.md`): wordfreq data and everything derived from it (per-word values, review sheets, aggregate manifests) stay out of the repository. The rule is not changed.

| Class | What it covers | Found in versioned files | Action |
|---|---|---|---|
| 1. Individual data | Per-word frequencies, review sheets | None. The curated CSVs have no frequency column; `frequency_report.py` is code | None |
| 2. Derived per-word or per-group data | Flags or labels computed from a word's frequency | None | None |
| 3. Aggregate statistics | Counts of words in a band, per-field medians or ranges | In `docs/phase-2b-design.md`, sections 3.3 and 6, added by `1ed5b5f` (a minimum count per field, exact counts for three fields, a median comparison between fields) | **Removed** from the current text; regenerated locally by `frequency_report.py` |
| 4. Design parameters of this project | The Zipf band bounds [3.2, 4.6) and the step of 0.1, and the threshold `t` | `docs/phase-2b-design.md` section 3.3 | **Kept** as our own parameters, stated without the counts that justified them. This is an interpretation, not a license finding: the project owner may instead have the bounds removed |
| 5. Statements about the resource | Pinned version, snapshot date, meaning of Zipf 0, the scale | `decisions.md` (D17), `research.md`, `phase-2b-design.md` | None; they quote no data |

**Not done, and not concluded.** History is not rewritten: `1ed5b5f`, in the private research repository, still contains the class 3 statistics. That history is not part of this distribution. This review draws no conclusion on whether CC BY-SA ShareAlike applies to them; that reading stays unresolved (see the table above).

**Forward item.** The `.gitignore` allows versioned `summary.md` and `manifest.json` files under `experiments/results/`. A future B10 run would produce wordfreq-derived values in those files. They must go to an ignored location or be left out of the versioned files; this is to be settled when B10 is implemented.

## Public release status (2026-11-18)

1. `NOTICE` and `THIRD_PARTY_NOTICES.md` exist and record the attributions above.
2. The current public distribution grants no license of its own for original material. Choosing one (Apache-2.0 is a possible future option) and the treatment of definitions from third-party sources stay open.
3. The DAMER/RAE terms, per-entry Wiktionary licenses, the MCR 3.0 equivalence and the wordfreq question remain unresolved; the data they concern is not part of this distribution.
4. `1ed5b5f` belongs to the history of the private research repository and does not affect this distribution.
