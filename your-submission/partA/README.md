# Part A — Tokenizer Fertility Audit

This directory contains code and artifacts for auditing the previous intern's tokenizer fertility report.

## Files

- `fertility_original.py`: Untouched copy of the starter kit fertility benchmark script.
- `build_corpus.py`: Script to construct the multilingual parallel evaluation corpus from FLORES-200.
- `audit_experiments.py`: Suite of isolating experiments validating and measuring each flaw in `fertility.py`.
- `AUDIT_FINDINGS.md`: Human-readable A2 findings with an exact command, before/after values, and a one-sentence proof for every claim.
- `corrected_analysis.py`: Corrected multi-tokenizer, multi-denominator analysis with pinned tokenizer revisions and paired bootstrap confidence intervals.
- `recommendation_memo.md`: Executive recommendation memo summarizing findings and production metrics.
- `data/`: Evaluation dataset and dataset metadata.
- `data/corpus_metadata.json`: Machine-readable A1 provenance, source hashes,
  preprocessing, language coverage, and generated-corpus hash.
- `results/`: Execution outputs (`baseline.csv`, `audit_deltas.csv`,
  `corrected_metrics.csv`, and `analysis_metadata.json`).

## Part A1 command

Rebuild the verified aligned corpus and its metadata:

```bash
python partA/build_corpus.py
```

The build fails on an unexpected archive hash, unequal line counts, or any
empty aligned row instead of silently changing alignment.

## Part A2 commands

Run the complete audit:

```bash
python partA/audit_experiments.py
```

Run one claim in isolation:

```bash
python partA/audit_experiments.py --experiment split_spaces
python partA/audit_experiments.py --experiment lowercase
python partA/audit_experiments.py --experiment macro_average
python partA/audit_experiments.py --experiment character_unit
python partA/audit_experiments.py --experiment parallel_denominator
python partA/audit_experiments.py --experiment nfc_control
python partA/audit_experiments.py --experiment random_seed_control
```

## Part A3 command

Run the complete corrected analysis:

```bash
python partA/corrected_analysis.py
```

Inspect one tokenizer without overwriting the complete CSV:

```bash
python partA/corrected_analysis.py --tokenizer gpt2
python partA/corrected_analysis.py --tokenizer indicbert
python partA/corrected_analysis.py --tokenizer qwen2.5
```

The analysis applies NFC consistently, preserves case and punctuation, uses
pooled totals for secondary denominators, and uses tokens per aligned sentence
relative to English as the headline routing measure.
