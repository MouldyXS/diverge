# Embedding PoC, Phase 2a: technical summary

Generated 2026-11-04T01:49:40.961615+00:00 by `experiments/embedding_poc/run_poc.py`. Technical checks only (evidence level E0); no semantic conclusion is drawn from any input.

**Overall: PASS** (A PASS, B PASS, C PASS; D is descriptive).

**Relation to the earlier Phase 2a work.** This run extends `experiments/check_2a_correctness.py` and its results in `experiments/results/2a_20261103_004339/`, which already checked Sentence Transformers against the reference implementation and reproducibility (all passed) and are not replaced. Their two criteria are reused unchanged; this run adds staged pooling/normalization checks, Unicode, batch and order checks, performance, memory and a pytest suite.

## Environment

- Python 3.12.10, torch 2.15.0+cpu (CUDA build: None; CUDA available: False), transformers 5.22.1, sentence-transformers 6.2.0, numpy 2.5.4, huggingface_hub 2.4.0, tokenizers 0.23.3, pytest 9.2.0.
- Genuine Intel(R) 0000, 12 cores / 16 logical, 31.7 GiB RAM, Windows-10-10.0.19044-SP0; torch threads 12.
- Model `ibm-granite/granite-embedding-278m-multilingual` at revision `a9cb5338491faf32b73dd17b714a31821c021bbf` (`model.safetensors` SHA-256 `b522423ae15d1a6fd48c55ef4f599c0c2c0737603da94e4b4815760c2c06ebac`), fp32 on CPU. Git commit c7a5825.

## Architecture and pooling (read from the snapshot, then confirmed on the loaded model)

- Architecture `XLMRobertaModel`, 12 layers, 12 heads, hidden size 768, vocabulary 250002, weights stored as bfloat16, maximum sequence length 512.
- `modules.json` declares Transformer -> Pooling -> Normalize; `1_Pooling/config.json` sets `pooling_mode_cls_token = True` and every other mode false.
- Sentence Transformers built Transformer -> Pooling -> Normalize; pooling mode `cls`; effective attention `sdpa`.
- Pooled CLS vectors have norms 18.83 to 19.70 (not unit); the Normalize module brings them to norm 1. So the three stages are separate: transformer output, CLS pooling, one L2 normalization.

## Tolerances (fixed before the first run)

| Quantity | Tolerance | Source |
|---|---|---|
| Cosine between paths | at least 0.99999 | acceptance-criteria-2c.md section 3 |
| Repeat, batch, order, fresh process | at most 1e-06 absolute | acceptance-criteria-2c.md section 3 |
| Max absolute difference, two paths | at most 1e-05 | `embedding.py` |
| Norm deviation from 1 | at most 1e-05 | `embedding.py` |

## A. Load (PASS)

- Load time 4.7 s (weights already in the local cache); working set 198.7 MiB before, 1774.9 MiB after load.
- Output shape [12, 768], finite: True, null vectors: 0, norms 0.9999999 to 1.0000001.

## B. Pooling and normalization (PASS)

- Token ids identical in both paths: True.
- Final vectors: min cosine 1.000000000, max absolute difference 0.000e+00, mean absolute difference 0.000e+00; norm deviation 1.19e-07 (Sentence Transformers) and 1.19e-07 (explicit).
- Pooled CLS vector before normalization, largest relative error 0.000e+00. Pooled vector divided by its own norm vs final vector: 2.980e-08.
- Sensitivity control: a mean-pooled vector gives a minimum cosine of 0.9639 against the reference, so a wrong pooling would be rejected by the same check.
- Attention: sdpa (Sentence Transformers) and sdpa (explicit).
- Limitation: A second L2 normalization is idempotent on unit vectors, so duplicated normalization cannot be seen in the final vectors; it is excluded by the module list (one Normalize), by the encode() defaults (normalize_embeddings=False) and by the raw CLS norms (not 1) in the stages.

## C. Reproducibility (PASS)

| Comparison | Max absolute difference |
|---|---|
| same session repeat | 0.000e+00 |
| one text per call | 5.960e-08 |
| reversed order | 0.000e+00 |
| fresh process | 0.000e+00 |
| batch size 1 vs reference | 5.960e-08 |
| batch size 2 vs reference | 4.470e-08 |
| batch size 5 vs reference | 4.470e-08 |
| batch size 64 vs reference | 0.000e+00 |

- Order sensitivity: swapping two rows changes the matrix by 8.261e-02, far above the tolerance, so an order error would be detected.
- Unicode: no unknown token in NFC or NFD forms: True; NFD and NFC token ids equal: True; NFD vs NFC vectors differ by at most 0.000e+00; upper-case, mixed-script and emoji inputs finite: True.

## D. Performance (descriptive; no thresholds)

- First inference (one text, includes warm-up): 24.64 ms; second: 16.99 ms; later single-text calls: median 17.16 ms (min 16.66, max 20.8).
- 64 texts, 5 repetitions each, median per run:

| Mode | Run ms | ms per text |
|---|---|---|
| one text per call | 1232.65 | 19.26 |
| batch size 1 | 1140.4 | 17.82 |
| batch size 8 | 228.13 | 3.56 |
| batch size 32 | 168.59 | 2.63 |
| batch size 64 | 170.9 | 2.67 |

- Ten texts in one request (batch size 32): median 40.6 ms.
- Memory at the end of the run (two model copies loaded: Sentence Transformers and explicit): working set 3200.6 MiB, peak 3263.1 MiB, private 4476.0 MiB.

## Limits

- Only fp32 was tested: the weights are stored as bfloat16 and run here as an exact upcast; bf16 inference was not tested.
- Reproducibility was checked in the current environment (one machine, the installed versions, one fresh process). Other machines, other library versions and a clean installation were not tested.
- Timings are descriptive measurements from one session with other processes running; they are not a benchmark.
- Installing `requirements-poc.txt` into an empty virtual environment has not been tested.
- The input set is tiny and fixed. Passing says the extraction is technically correct and reproducible; it does not show semantic quality.
