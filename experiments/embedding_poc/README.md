# Granite embedding PoC (Phase 2a, technical checks)

Checks that `ibm-granite/granite-embedding-278m-multilingual` loads and produces correct, reproducible embeddings on CPU, and that the pooling and normalization really applied are the ones the model declares. **Technical only (evidence level E0).** It does not ask whether the model separates related from unrelated words (that is Phase 2b), computes no similarity between different words, and is not part of the future application.

> **Public distribution.** This repository is an independent public distribution of Diverge v0.1.0-beta.1, prepared from the current state of a separate research repository. Historical commit identifiers, tags, backup locations and datasets mentioned in research documents refer to that private repository and are not part of this distribution. Internal research datasets and validation resources are not included.

## Relation to the earlier Phase 2a work

This PoC **extends** the Phase 2a checks; it is not the first validation of those criteria. `experiments/check_2a_correctness.py` (commits `0032ced` and `51ce75e` of the private research repository, not part of this distribution) already compared Sentence Transformers with the reference implementation and checked reproducibility, and its results in `experiments/results/2a_20261103_004339/` (all checks passed) remain valid and are not replaced. Its two criteria are reused here unchanged: cosine at least 0.99999 and reproducibility within 1e-6 (`docs/acceptance-criteria-2c.md` section 3). What this PoC adds: pooling and normalization read from the model's own files and separated into stages, a mean-pooling sensitivity control, Unicode inputs, batch-size and order checks, performance and memory, and a pytest suite.

## What is checked

| | Check |
|---|---|
| A | Loads on CPU in fp32; 768 dimensions; finite values; no null vectors; load time and memory |
| B | Pooling and normalization read from the model's own files, then confirmed on the loaded model; Sentence Transformers (reference) vs an explicit path (Transformers `AutoModel`, first-token output, one L2 normalization): token ids, pooled vector before normalization, final vector |
| C | Same input twice, one text per call vs batches of several sizes, reversed order, fresh process, NFD vs NFC input, upper-case / mixed-script / emoji input |
| D | First inference vs later ones, one text per call vs batch sizes 1, 8, 32 and 64, a ten-text request; descriptive, no thresholds |

Fixed inputs: `casa`, `perro`, `árbol`, `canción`, `año`, `ñandú`, `guagua`, `chuchaqui`, `canguil`, `casa de campo`, `perro caliente`, `hasta luego`.

## Tolerances (fixed before the first run)

| Quantity | Tolerance | Why |
|---|---|---|
| Cosine between the two paths | at least 0.99999 | `docs/acceptance-criteria-2c.md` section 3, reused unchanged |
| Repeat, batch, order, fresh process | at most 1e-6 absolute | same document, reused unchanged |
| Maximum absolute difference, two paths | at most 1e-5 | Same fp32 network on CPU; only padding and operation order may differ. fp32 epsilon is 1.2e-7, components are about 0.04, and a real defect (wrong pooling, missing or double normalization) changes components by 1e-1 or more |
| Norm deviation from 1 | at most 1e-5 | fp32 unit vectors deviate by a few 1e-7 |

Do not loosen a tolerance to make a check pass: investigate the cause.

## Requirements

- Windows, Python 3.12, the project's virtual environment `.venv` at the repository root (not the ComfyUI or Stability Matrix environments).
- Versions that produced the results: `requirements-poc.txt`. The tested torch is **`2.15.0+cpu`**, which comes from the official PyTorch CPU wheel index (`https://download.pytorch.org/whl/cpu`; the file lists `torch-2.15.0+cpu-cp312-cp312-win_amd64.whl`). The requirements file pins `torch==2.15.0+cpu` and carries `--extra-index-url` for that index, so one command installs everything: `.venv\Scripts\python.exe -m pip install -r experiments\embedding_poc\requirements-poc.txt`. PyPI also lists a plain `torch-2.15.0` wheel for Windows; it is a different file and was not tested.
- **Not yet tested: installing from this file into an empty virtual environment.** The versions record what is installed in the existing `.venv`. The only check done was `pip install --dry-run -r requirements-poc.txt` against that environment (the file parses, every pin is already satisfied, nothing was installed) and a look at the wheel index.
- The model weights stay **outside the repository**, in the Hugging Face cache (`%USERPROFILE%\.cache\huggingface\hub`), pinned to revision `a9cb5338491faf32b73dd17b714a31821c021bbf`. The scripts run offline (`HF_HUB_OFFLINE=1`). To download the pinned revision once, set `DIVERGE_POC_ALLOW_DOWNLOAD=1` for that run (about 575 MB for the files the model needs).
- To download the pinned revision with the same command as the main README (nine named files, about 544 MiB; `hf` comes with `huggingface_hub`, see "Getting the model" in `README.md` for the dry run and for how to run it):

  ```powershell
  hf download `
    --revision a9cb5338491faf32b73dd17b714a31821c021bbf `
    ibm-granite/granite-embedding-278m-multilingual `
    "1_Pooling/config.json" `
    "config.json" `
    "model.safetensors" `
    "modules.json" `
    "sentence_bert_config.json" `
    "sentencepiece.bpe.model" `
    "special_tokens_map.json" `
    "tokenizer.json" `
    "tokenizer_config.json"
  ```

## Run (from the repository root)

```
.venv\Scripts\python.exe -m pytest experiments\embedding_poc\tests -q
.venv\Scripts\python.exe experiments\embedding_poc\run_poc.py
```

Expect `15 passed` and `overall: PASS`. The run takes about a minute. It writes to `experiments/results/embedding_poc_2a/`:

- `manifest.json` and `summary.md`: versionable under the `.gitignore` rules (library versions, model revision and file hash, machine, tolerances, every number);
- `reference_st.npy`, `explicit_cls_l2.npy`: raw embeddings, ignored by Git.

Timings in `summary.md` depend on the machine and on what else is running; they are descriptive.

## Files

- `embedding.py`: the two extraction paths, tolerances, helpers (no application code, no network by default);
- `run_poc.py`: experiments A to D and the report;
- `tests/test_embedding.py`: pytest suite (each test is independent; the model is loaded once per module);
- `requirements-poc.txt`.

## Limits

- Only fp32 was tested. The weights are stored as bfloat16 and run here as an exact upcast; bf16 inference was not tested.
- Reproducibility was checked in the current environment (same machine, same installed versions), including one fresh process. It says nothing about other machines, other library versions or a clean installation.
- Timings are descriptive measurements from one session with other processes running; they are not a benchmark and no performance threshold exists.
- A clean installation has not been tested (see Requirements).
- A duplicated L2 normalization cannot be seen in the final vectors (it is idempotent), so it is excluded structurally: one `Normalize` module, `normalize_embeddings` left False in `encode`, and pooled vectors that are not unit vectors before that module.
- When both paths pad a batch the same way, a difference of exactly zero is expected; it does not mean the paths share code. The mean-pooling control shows the comparison would reject a wrong pooling.
- A tiny fixed input set proves technical correctness only. **It does not show semantic quality**; that is Phase 2b.
