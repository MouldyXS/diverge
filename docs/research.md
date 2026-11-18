# Research notes

Status: Phase 1 draft, 2026-11-02; section 9 added 2026-11-03. Language: English (technical documentation).

Labels: **FACT** = verified in a consulted source; **PROPOSAL** = design decision, open to discussion; **UNCERTAIN** = not verified or to be checked in the proof of concept.

## 0. Provenance and verification status

- The PMC page of Olson et al. (2021) is protected by a reCAPTCHA. Its content was read through the Europe PMC full-text XML endpoint.
- The S-DAT paper was read through the arXiv HTML version (v2).
- Both passed through an automatic text extractor. They were **not** read directly from the PDFs.
- **Cross-check, 2026-11-03:** a second extraction pass verified the figures below claim by claim against the same source texts (Europe PMC XML and arXiv HTML v2). Every number in sections 1–2 matched the paper text. The pass also produced the corrections listed in section 0.1.
- **UNCERTAIN:** the check was still not made against the PDFs themselves. An attempt to extract text from the PDF with the standard library failed (no PDF rendering tool is installed). Quote figures in the README or any publication only after a manual look at the PDF.

### 0.1 Corrections made after the cross-check

- The DAT paper states only that GloVe was trained on Common Crawl. The 840B-token model with 300 dimensions comes from the reference code repository, not from the paper.
- The DAT paper lists dependence on the model and corpus under future research, not under its limitations section.
- S-DAT Table 1 marks nomic-embed-text-v1.5 and snowflake-arctic-embed-l as non-multilingual, while Section 3 calls all eight models multilingual.
- S-DAT does not state the language of the AUT, nor explicitly that the 100 calibration nouns were English; both are inferences. The validation samples are Australian.
- The abstract of S-DAT speaks of "robust and consistent scoring", but the paper reports no reliability statistics for S-DAT.

## 1. Original DAT (Olson et al., 2021)

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC8237676/ · code: https://github.com/jayolson/divergent-association-task

- **FACT:** participants name 10 nouns that are as different as possible, in 4 minutes. No proper nouns or specialized terms. Words must be in a common dictionary and lowercase to be scored.
- **FACT:** only the **first 7 valid words** are scored; the extra three are a buffer against typos and words missing from the model. Seven was chosen as a balance between inclusion rate and correlation with the Alternative Uses Task (AUT).
- **FACT:** GloVe trained on Common Crawl (the 840B-token, 300-dimension model is named in the code repository, not in the paper). Score = mean cosine distance over the 21 pairs of the 7 words, times 100. Theoretical range 0–200; in practice 65–90, rarely above 100; below ~50 often indicates misunderstood instructions (e.g. naming opposites).
- **FACT:** Study 1A (n=141): M=78.38, SD=6.35. Study 2: n=8,572, 98 countries.
- **FACT:** convergent validity with the AUT: flexibility r≈.34–.35 and originality r≈.32 in full samples (r≈.50 in a hand-screened subset); r=.13 in Study 2 with a shortened AUT. Test–retest at two weeks r=.73 (n=50).
- **FACT:** limitations stated by the authors: originality is measured better than appropriateness; scores may partly reflect over-inclusive thinking; the task can be gamed (rare words, letter-based patterns). Dependence on the model and corpus is raised in the future-research discussion.
- **FACT:** the reference implementation validates words against a Hunspell-based list (`words.txt`) and uses `glove.840B.300d.txt`. Its README sets no explicit minimum number of words.

## 2. S-DAT (Haase, Hanel and Pokutta, 2025)

Source: https://arxiv.org/abs/2505.09068 (HTML: https://arxiv.org/html/2505.09068v2)

- **FACT:** replaces GloVe with multilingual embeddings. Eight models were compared (Table 1 marks two of them, nomic-embed-text-v1.5 and snowflake-arctic-embed-l, as non-multilingual): OpenAI text-embedding-3-large, nomic-embed-text-v1.5, snowflake-arctic-embed-l and -l-v2.0, granite-embedding-278m-multilingual, e5-mistral-7b-instruct, multilingual-e5-large-instruct, bge-m3.
- **FACT:** Granite was chosen for the best cross-language calibration (stable distance distributions, including non-Latin scripts) and because it is open-weight. The explanation that synthetic training pairs cause this is the authors' interpretation, not a tested result.
- **FACT:** calibration described as a linear transformation matching the mean and standard deviation of the DAT's GloVe distances, using 100 nouns translated into each language (that the source nouns are English is an inference, not an explicit statement); the same transformation for all languages.
- **FACT:** published percentiles come from Olson's English Study 2 (Australian sample).
- **FACT:** S-DAT correlates .60–.67 with the DAT. With the AUT it is weaker than the DAT in Studies 1a/1b and equal in Study 2. No reliability statistics (test–retest, internal consistency) are reported for S-DAT. Human validation uses the Australian samples of the original DAT study; the AUT language is not stated but is inferred to be English, so there is no human validation in Spanish.
- **FACT:** the number of languages is inconsistent (11 in the abstract, 15 in Table 2); one coefficient is flagged significant with a confidence interval that includes zero.

### 2.1 What could not be verified about the original implementation

- **FACT:** Section 2.4 says the DAT averages "the top seven words" and also that ten words yield 45 pairs. The paper does not say how many words S-DAT scores or how it treats duplicates and invalid words.
- **FACT:** the calibration coefficients and the 100-noun list are not given in the text. No code repository is declared.
- **FACT:** the OSF project of the paper holds three CSV files of Olson (2021) human-rated data and an R script (`DAT 2.0 R-code.R`). The script reads the data, runs correlations, regressions and plots, and defines a helper for empirical percentiles. It does **not** compute S-DAT scores and contains **no calibration constants**.
- **UNCERTAIN:** the CSV files were not inspected; they may include per-participant S-DAT scores.
- **FACT:** the online tools (https://sdat.iol.zib.de/, https://cap.ist.psu.edu/sdat) do not document a scaling. The Penn State tool accepts at least two unique words per response and averages distances; responses with duplicate words cannot be scored.

## 3. Granite Embedding 278M Multilingual

Source: https://huggingface.co/ibm-granite/granite-embedding-278m-multilingual

- **FACT:** XLM-RoBERTa encoder, 12 layers, 12 heads, 768-dimensional embeddings, vocabulary 250,002, maximum 512 tokens, about 278M parameters. `config.json` stores weights as bfloat16.
- **FACT:** officially supported languages: en, ar, cs, de, **es**, fr, it, ja, ko, nl, pt, zh.
- **FACT:** license Apache-2.0. MS-MARCO was excluded from training because of its non-commercial license.
- **FACT:** Sentence Transformers pipeline: `Transformer → Pooling (CLS) → Normalize`. Output vectors are L2-normalized, so cosine similarity equals the dot product. The model card documents no query/passage prefixes or instructions.
- **FACT:** model card usage: `SentenceTransformer(path).encode(texts)`; the Transformers path takes the first-token output and applies `torch.nn.functional.normalize`.
- **PROPOSAL:** embed the normalized single word, in fp32, on CPU, one `encode` call per request, with a pinned model revision.
- **UNCERTAIN:** the model card does not document behavior on single words. Whether a bare word or a short template gives more consistent distances is decided in Phase 2 on the development partition.
- **UNCERTAIN:** memory in fp32 is estimated at ~1.1 GB of weights (278M × 4 bytes) if the model is loaded in fp32; to be measured.
- **FACT (queried 2026-11-03 through the Hugging Face API, no weights downloaded):** revision `a9cb5338491faf32b73dd17b714a31821c021bbf`, last modified 2025-08-19, license Apache-2.0. The repository holds `model.safetensors` (556.1 MB, bf16), `pytorch_model.bin` (1,112.2 MB), `model.onnx` (1,112.4 MB), `tokenizer.json` (9.1 MB) and `sentencepiece.bpe.model` (5.1 MB), plus small config files. The expected download is therefore about 575 MB (safetensors and tokenizer), not 1.1 GB; the `.bin` and `.onnx` copies should not be fetched.
- **UNCERTAIN:** `modules.json` lists a `2_Normalize` module, but no `2_Normalize` file appears in the repository listing. Whether Sentence Transformers 6.2.0 still applies L2 normalization is verified in Phase 2a (the check against the CLS + L2 reference covers it).

## 4. Software environment

Versions below were the latest on PyPI on 2026-11-02 and are **not** frozen (see CLAUDE.md §4, a private project-context file, not part of this distribution).

- **FACT:** torch 2.15.0 (requires Python ≥3.11); sentence-transformers 6.2.0 (requires `transformers>=5`, `torch>=2.2`, Python ≥3.10); fastapi 0.162.0; wordfreq 3.1.1.
- **FACT:** sentence-transformers 5.5.0, 5.5.1 and 5.6.0 degraded XLM-R embeddings only when Flash Attention 2 was explicitly requested with Transformers 5. The default SDPA path was not affected. Fixed in 5.6.1. (Corrected by the project owner; to be re-checked against the release notes.) Diverge runs on CPU with the default attention and does not use FA2.
- **FACT:** sentence-transformers 6.0 is a major release with breaking changes; migration notes are in the release page.
- **UNCERTAIN:** compatibility of Granite with sentence-transformers 6.2.0 and Transformers 5 is verified in Phase 2a.
- **FACT:** PyTorch deprecated CUDA 12.8 wheels; current CUDA wheels target CUDA 13.x. Not relevant while CPU is the baseline.

## 5. Lexical validation resources

### 5.1 wordfreq

Source: https://github.com/rspeer/wordfreq · sunset note: https://github.com/rspeer/wordfreq/blob/master/SUNSET.md

- **FACT:** word frequencies for 40+ languages, including a "large" Spanish list from seven sources (Wikipedia, subtitles, news, books, web, Twitter, Reddit). Frequencies use the Zipf scale (log10 of occurrences per billion words). Absent words return 0.
- **FACT:** accents are not stripped by the lookup: `cafe` and `café` are different entries.
- **FACT:** the data is a snapshot up to about 2021 and the author states it is unlikely to be updated.
- **Role in Diverge (PROPOSAL):** a lexical *frequency* resource, not a normative dictionary. Absence means "unknown to the resource", never "invalid".
- **UNCERTAIN:** its effect on false negatives for recent words and regionalisms is measured in Phase 2c.

### 5.2 Licenses and attributions (wordfreq)

- **FACT:** code under Apache-2.0. Some data files may be redistributed under CC BY-SA 4.0.
- **FACT:** acknowledgements requested for the Google Books Ngram Viewer and OpenSubtitles; SUBTLEX authors must be credited and SUBTLEX must remain clearly identified as freely available; a citation is requested (Speer, 2022, Zenodo, DOI 10.5281/zenodo.7199437).
- **FACT:** Twitter data was collected under Twitter's developer terms. NewsCrawl, GlobalVoices, OSCAR and Reddit have no license stated in the README.
- **PROPOSAL (approved):** wordfreq stays an experimental dependency installed only in the local environment; its data is not copied into the repository; no public Docker image includes it until the license conditions are reviewed. Policy P0 does not depend on it.
- **UNCERTAIN:** the legal reading of ShareAlike and of the sources without a stated license.

### 5.3 Excluded and reference resources

- **FACT:** spaCy `es_core_news_sm/md/lg` 3.8.0 are GPL-3.0 (trained on AnCora and WikiNER; require spaCy ≥3.8,<3.9). They are **excluded from the MVP**.
- **UNCERTAIN:** part-of-speech and named-entity tagging on isolated words is expected to be unreliable; any POS-like or proper-noun heuristic is advisory and its precision is measured before it is kept.
- **FACT:** the DAMER (ASALE) dictionary of Americanisms is available online (https://www.rae.es/recursos/diccionarios/damer); a printed reference for Ecuador is Córdova Malo, *El habla del Ecuador. Diccionario de ecuatorianismos* (USFQ Press, 3rd ed., 2019). They are references for labeling. From DAMER, the word sets record only country marks, a sense number and a short paraphrased gloss; definitions are not copied. DAMER was read through an automatic text extractor (2026-11-03); Córdova Malo was not consulted. **UNCERTAIN:** DAMER reuse terms. The DLE returned HTTP 403 to automated access and was not consulted.

## 6. Normalization and duplicates

- **PROPOSAL (approved):** `strip` → NFC → `casefold` → NFC. Spanish diacritics and ñ are preserved.
- **PROPOSAL (approved):** duplicates are exact matches after normalization. Diacritic-only matches (sí/si, él/el, año/ano, papá/papa, té/te, sé/se) are distinct words and only produce a heuristic warning.

## 7. Methodological limitations

- No human-criterion validation exists for this embedding model in Spanish. Diverge makes no psychometric claim (evidence level E3 is not claimed). Evaluation with human participants is postponed (`future/human-evaluation.md`).
- Transformer embeddings have no out-of-vocabulary words: nonsense strings receive embeddings and may score high. **UNCERTAIN** magnitude; measured in Phase 2.
- Antonyms are close in embedding space; polysemy, plurals and misspellings affect distances.
- Scores are not comparable with DAT or S-DAT scores (see `scoring.md`).
- Cosine distance is not bounded to [0, 1]; its theoretical range is [0, 2].

## 8. Open items

- Look at the PDFs manually before quoting any figure publicly (the text-level cross-check is done; see section 0).
- Record the Granite revision hash.
- Inspect the OSF CSV files (optional).
- Contact the S-DAT authors about calibration (postponed, decision D10).
- Review wordfreq license conditions before any public distribution.
- Items opened by section 9 (verbatim quotations, licenses of cited entries, MCR equivalence, RAE terms) are tracked in `third-party-review.md` and `decisions.md`.

## 9. Lexical resources used as word-set evidence (added 2026-11-03)

Used to support or contradict the `close`/`related` labels of the triplets and to assign nouns to fields (`phase-2b-design.md`, section 8). They never enter the scoring path. Observed on 2026-11-03 with `wn` 1.1.1, `omw-es:2.0` and `omw-en:2.0`, reading the XML and the library code.

- **FACT:** `omw-es:2.0` has 78,948 synsets and **0 semantic relations**; it declares a dependency on `omw-en:2.0`. Earlier hierarchy results therefore came from `omw-en` through the ILI, and are not Spanish evidence.
- **FACT:** `omw-es:2.0` carries its own Spanish definitions for 19,444 synsets and 93,834 lemmas, all in NFC. It has no `<Form>` elements, so `search_all_forms` changes nothing and inflected forms cannot be detected from it (`perros` is a lemma of its own).
- **FACT:** each ILI declared in `omw-es:2.0` matches exactly one synset of `omw-en:2.0`; 6,429 adjective synsets have different id suffixes, so offsets or ids are not a safe crosswalk. The ILI is used instead.
- **FACT:** the default `wn` normalizer strips diacritics and case. Measured effect on the earlier audits: 1 of 150 audited pairs changed; the lookups of 3 triplet words, 9 noun words and 2 regional words returned different senses. Later audits use exact lookup.
- **FACT:** `*INFERRED*` is a runtime constant of `wn/_core.py`, not data in the resource. The earlier audits ignored synsets with that marker and may have cut ancestor chains, so some `not_found` taxonomic results can be incomplete.
- **FACT:** the noun hypernym graph of `omw-en:2.0` (82,115 synsets) is acyclic; 1,422 nouns have several parents (maximum 5).
- **PROPOSAL:** Spanish Wiktionary data (through the kaikki extraction, not yet transferred) supplies Spanish definitions and sense labels; English Wiktionary never corroborates a Spanish sense. Each quotation is recaptured verbatim with URL and date or revision.
- **UNCERTAIN:** the equivalence of `omw-es:2.0` with MCR 3.0; per-entry Wiktionary licenses; the DAMER/RAE reuse terms (the site returned HTTP 403 to automated access).
