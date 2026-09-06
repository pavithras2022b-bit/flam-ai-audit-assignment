# AI Usage Disclosure

## What AI generated

Antigravity generated the initial repository structure and nearly all of the
first-draft code, CSV outputs, notebook entries, calculations, and memos. That
draft was treated as a starting hypothesis, not as verified work.

## How ChatGPT helped with the audit

ChatGPT unpacked the submitted ZIP, compared the code with the assignment,
executed the reproducible scripts in a clean environment, and identified
contradictions between calculated values and written conclusions. It then
helped rebuild Part A2 so that every claim has an isolated command,
before/after numbers, and a conclusion generated from those numbers.

During the final audit, ChatGPT also strengthened the Part A1 corpus builder.
It added exact source-hash verification, safe extraction of only the required
files, alignment checks before whitespace cleanup, deterministic LF output,
and machine-readable corpus metadata. It also created a repository verifier
and a short defense guide. These aids check consistency; they do not replace
my responsibility to understand and defend the work.

## Where the original AI draft misled

The original draft:

- reversed the direction of the lowercasing result;
- mixed stale grapheme, NFC, and sentence-ratio values into conclusions;
- treated the non-parallel starter samples as matching translations;
- called a disconnected CSV-patching script evidence even though the master
  runner overwrote its changes;
- claimed full personal verification and 100% defense readiness without an
  honest chronological basis;
- included unsupported serving and training claims in later memos.

These claims were not retained merely because they sounded confident.

## What has been independently rerun so far

During the review, the following were executed successfully:

- the untouched v0 baseline;
- all seven Part A2 experiments individually;
- the complete Part A2 audit;
- a repeat run confirming an identical generated evidence CSV;
- the complete Part A3 analysis in a newly created environment using only the
  pinned `requirements.txt` dependencies;
- a second Part A3 run confirming identical result and metadata file hashes;
- the one-tokenizer command, confirming that it does not overwrite the full
  21-row result table;
- the corrected Part B script, including independent checks that
  `reported_tok_s` counts prompt plus generated tokens, the two goodput
  formulas agree within rounding, and the model-spec capacity predicts the
  observed preemption boundary;
- the integrated `python run_all.py --skip-corpus` command, confirming Parts A
  and B complete successfully together in the clean environment;
- the Part C arithmetic and reviewer-budget allocation. No Part C experiment
  result is claimed because the proposed Day-1 review has not been run.
- the Part A1 builder twice, confirming identical corpus and metadata hashes;
- negative Part A1 tests confirming that a blank aligned row and a corrupted
  archive are rejected;
- the repository-level verifier covering required files, hashes, row counts,
  experiment IDs, result tables, memo length limits, and disclosure language.
- the complete `python run_all.py` pipeline twice with corpus construction
  enabled, followed by matching hashes for all generated A1, A2, A3, and Part B
  artifacts and a passing verifier after each run.

The corrected tokenizer table and the initial Part B goodput script were also
reproduced during diagnosis. ChatGPT revised Part A3/A4 to apply consistent
preprocessing, pooled secondary metrics, pinned tokenizer revisions, a corpus
hash, and careful model-tokenizer compatibility language. It then rebuilt Part
B's memory arithmetic, throughput diagnosis, two goodput derivations,
concurrency-cap prediction, and monitoring-counter answer. The revision labels
the two-wave result as a prediction rather than a measured benchmark and does
not invent a p95-latency improvement. For Part C, ChatGPT removed unsupported
training-time, latency, and memory claims; changed the three-week recommendation
from immediate SFT to a reversible prompt-only test; and made the absence of
native review for four languages an explicit launch blocker rather than hiding
it behind an automated judge.

## Personal verification still required before submission

Before submitting, I will:

- [x] run the complete pipeline and repository verifier on my own machine;
- [x] record any setup failures or changed results in `NOTEBOOK.md`;
- [x] remove or rewrite any claim I cannot defend;
- [] complete a live mock-defense session.

This disclosure will be updated after those steps rather than claiming they
have already happened.
