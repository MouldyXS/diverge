# Scoring protocol

Status: Phase 1 draft, 2026-11-02; amended 2026-11-03 (P0 provisional, user notice in section 8). Labels as in `research.md`: **FACT**, **PROPOSAL**, **UNCERTAIN**.

## 1. Official protocol: `dat7`

**PROPOSAL (approved).**

1. Normalize each of the ten entries: `strip` → NFC → `casefold` → NFC.
2. Validate (deterministic rules, then the active validation policy; see `research.md` §6 and the policy section below).
3. Keep the **first seven eligible, unique** words, in order of entry. "Eligible" means valid, unique and admitted by the active policy.
4. Embed the seven words with `ibm-granite/granite-embedding-278m-multilingual`. Vectors are L2-normalized by the model.
5. Compute the 21 pairwise distances: `distance(A, B) = 1 − cosine_similarity(A, B)`.
6. `index = mean(pairwise_distances) × 100`.

If fewer than seven eligible words remain, **no score is produced**. The response lists every entry with its status and reasons.

## 2. Scale

- **FACT:** cosine distance lies in [0, 2], so the index lies in [0, 200]. Multiplying by 100 does not make it a 0–100 score.
- **PROPOSAL (approved):** the theoretical range 0–200 is kept. No clipping, rescaling, percentiles, rankings or "population averages".
- The empirical range obtained with Granite is measured in Phase 2b. Any reference values shown to users come from our own measurements and are labeled "model reference, not a population norm".

## 3. Experimental variant: `all10`

**PROPOSAL (approved as experimental).** Mean of the 45 distances among ten eligible words, times 100. It exists only in the proof of concept, as an "own exploratory variant". It is **not** presented as a reproduction of S-DAT, because the original implementation could not be verified (`research.md` §2.1). It is never shown to end users.

## 4. S-DAT calibration: not implemented

- **FACT:** S-DAT describes a linear transformation that matches the mean and SD of the DAT's GloVe distances, but publishes no coefficients and no 100-noun list, and no code repository was found.
- **PROPOSAL (approved):** do not implement it. Keep raw Granite scores.
- **Consequence:** the Diverge index is **not numerically comparable** with DAT or S-DAT scores, and the published English percentiles do not apply.
- Revisit only if the coefficients become verifiable (for example through the authors, decision D10) or if our own documented calibration is justified by evidence. Any future calibration must be documented separately from this formula.

## 5. Validation policies (experimental, undecided)

Policies P0/P1/P2 differ only in which words are *eligible*; the scoring formula is the same. Decision D3 was to be made after the Phase 2c evaluation.

**Update 2026-11-03.** Phase 2c is deferred. **P0 is adopted as a provisional product decision**, not as a result of Phase 2c. P0 cannot meet the false-positive criterion for nonexistent strings (at most 5%), because no deterministic rule blocks them; the adoption is not evidence that P0 passes. P1 and P2 stay documented and are not implemented. The scoring formula does not change. See `acceptance-criteria-2c.md`, amendment 3.

| Policy | Rule | Notes |
|---|---|---|
| P0 permissive | Only deterministic rules block. Everything else is a warning and the word is scored. | Does not need wordfreq. |
| P1 strict | Also, a word with Zipf frequency below `t` is not scored; it stays visible as `unknown_to_lexicon`. | `t` chosen on the development partition only. |
| P2 intermediate | A word below `t` cannot occupy one of the seven slots until the user confirms it. | Confirmation is a **validity attestation by the user**, not automatic detection. Confirmed words are marked in the result. |

Heuristics (frequency, verb/adjective ending, proper-noun capitalization, specialized-term frequency, singular/plural, diacritic-only match) never block a word on their own.

## 6. Output contract (planned)

Every result includes: `index`, the seven words used, the 7×7 distance matrix, the three closest and three most distant pairs, the excluded or warned entries with reasons, `protocol` (`dat7`), `protocol_version`, `model_id`, `model_revision` and `validation_policy`. While P0 is active the result also shows the notice of section 8.

## 7. Interpretation and limits

- The index is a "semantic divergence index" (*índice de divergencia semántica*). It does not measure intelligence, personality or overall creative ability.
- **UNCERTAIN:** it has no demonstrated psychometric validity in Spanish (evidence level E3 is not claimed).
- Known effects: antonyms look close; polysemy, plurals and typos change distances; nonsense strings may inflate the index (to be measured).
- The task can be gamed with rare or invented words, as acknowledged by Olson et al. (2021).
- Under P0 the server checks only the format of each entry (one word, no digits or symbols, no repetition). It does not check that the word exists in Spanish or that it is a noun.
- Timing is enforced by the client only; the server is stateless.

## 8. User notice under P0 (Spanish interface copy)

Shown with every result while P0 is the active policy. The wording is the project owner's. It is interface text, so it stays in Spanish.

> Diverge solo revisa el formato de lo que escribes: una sola palabra, sin números ni símbolos, y sin repetir. No comprueba que la palabra exista en español ni que sea un sustantivo.
>
> El modelo puede generar una representación numérica incluso para palabras inventadas o con erratas. Eso no significa que haya comprendido su significado.
>
> El índice calcula las distancias entre esas representaciones. No mide tu creatividad, tu inteligencia ni tu personalidad.

Do not describe the index as validated, as a percentile or as comparable with DAT or S-DAT scores.
