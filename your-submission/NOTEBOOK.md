# Lab Notebook

This notebook begins with the independent audit of an AI-generated first
draft. The original Antigravity-generated ZIP is preserved unchanged.

## 2026-09-05 - Starting state and audit plan

### Starting state

Antigravity generated the initial repository, scripts, CSV results, notebook,
AI-usage statement, and written memos. I had not independently derived every
number in that draft. Therefore, the initial notebook's claim that the
submission was "100% defense-ready" was not accepted as evidence.

### Plan

Audit one section at a time, beginning with Part A2. For each claim:

1. Run one isolated command.
2. Record the measured before/after values.
3. Check that the written direction matches the numbers.
4. Keep only claims that can be defended.

## 2026-09-05 - Reproduce the v0 baseline

### Hypothesis

The untouched starter script should reproduce the numbers in
`REPORT_v0.md`.

### Command

```bash
python partA/fertility_original.py \
  --corpus eng=../starter_kit/starter_kit/corpus_sample/eng_sample.txt \
  --corpus hin=../starter_kit/starter_kit/corpus_sample/hin_sample.txt \
  --tokenizer gpt2
```

### Result

English fertility `1.27`, Hindi fertility `7.45`, and Hindi/English ratio
`5.89x`. The baseline was reproduced.

### Revision

Use this result only as the before value. Do not treat the report's
interpretation as proven.

## 2026-09-05 - Dead end found in the AI-generated A2 draft

### Hypothesis

The existing conclusions should match `audit_deltas.csv`.

### Experiment

Read each generated row and compare its numbers with the hard-coded conclusion
in `audit_experiments.py`.

### Result

They did not match:

- The code measured English raw `96` to lowercased `99` tokens, but the prose
  said lowercasing reduced the count.
- The grapheme experiment produced `2.4415`, but the prose said `2.18`.
- The NFC experiment produced `459` Hindi tokens, but the prose said `477`.
- The denominator experiment produced `6.11x` and `4.78x`, but the prose said
  `5.89x` and `4.39x`.

### Revision

Discard the old A2 evidence table and rebuild each result directly from the
measured values. Remove hard-coded conclusions that can drift away from the
calculation.

## 2026-09-05 - FLAW-1: literal-space splitting

### Command

```bash
python partA/audit_experiments.py --experiment split_spaces
```

### Result

The double-spaced English line is counted as 8 items by `split(" ")` and 7
words by `split()`. Its fertility changes from `1.2500` to `1.4286`. Across the
starter sample, the Hindi/English ratio changes from `5.8871` to `5.9221`.

### Interpretation

This is a real code bug. Its report-level effect is measurable but small:
fixing it increases the ratio by 0.59%.

## 2026-09-05 - FLAW-2: lowercasing

### Command

```bash
python partA/audit_experiments.py --experiment lowercase
```

### Result

On the starter sample, English changes from 96 raw tokens to 99 lowercased
tokens; Hindi remains 459. The report ratio is `5.8871` with lowercasing and
`6.0590` on raw text.

On FLORES, English changes from 27,044 raw tokens to 27,994 lowercased tokens;
Hindi changes from 200,467 to 200,475.

### Interpretation

The earlier AI-written direction was backwards. Lowercasing changes the metric
asymmetrically. Whether it is a flaw depends on the production contract: the
benchmark must tokenize the same text form the deployed model receives.

## 2026-09-05 - FLAW-3: aggregation

### Command

```bash
python partA/audit_experiments.py --experiment macro_average
```

### Result

With whitespace handling held fixed, mean-of-line fertility gives `5.922121`
and pooled corpus counts give `5.928465`.

### Interpretation

The aggregation choice changes the number, but only by 0.11% on this sample.
The small effect is reported rather than exaggerated.

## 2026-09-05 - FLAW-4: character definition

### Command

```bash
python partA/audit_experiments.py --experiment character_unit
```

### Result

The Hindi/English ratio is `6.9985` per Unicode code point and `10.8570` per
user-visible grapheme cluster.

### Interpretation

`len(text)` is not wrong Python; the problem is calling its output simply
"characters" and using that number to confirm a cross-language cost claim.

## 2026-09-05 - FLAW-5: conceptual denominator

### Command

```bash
python partA/audit_experiments.py --experiment parallel_denominator
```

### Result

On the same 1,012 aligned FLORES rows with GPT-2, Hindi/English is `6.3309x`
per whitespace word and `7.4126x` per aligned sentence.

### Interpretation

The word-based value is 14.59% below the aligned-sentence value. Matching
sentences are the more relevant unit because they approximately hold meaning
constant.

## 2026-09-05 - Controls

### Commands

```bash
python partA/audit_experiments.py --experiment nfc_control
python partA/audit_experiments.py --experiment random_seed_control
```

### Result and revision

NFC changes zero tokens in the v0 sample, so it is not a v0 bug. It changes the
seven-language FLORES total by 0.081%, so preprocessing must be consistent and
documented. Changing the random seed produces no change because the script
does not use randomness.

## Current checkpoint

Part A2 has been rebuilt and independently executed in a clean review
environment. The next work is to rerun these commands locally, add personal
observations in this notebook, and then correct Part A3/A4. Parts B and C from
the original AI draft are not yet approved for submission.

## 2026-09-05 - Part A3 methodology correction

### Problem found in the AI draft

The initial corrected analysis preserved raw text while the original script
applied NFC normalization. It also averaged per-line word, grapheme, and byte
rates instead of using pooled corpus totals. Tokenizer revisions were not
pinned, so a future download could silently change the result.

### Revision

The analysis now:

- applies NFC to every language while preserving case and punctuation;
- validates 1,012 complete, uniquely identified parallel rows;
- uses pooled totals for word, grapheme, and byte diagnostics;
- uses total tokens across aligned sentences divided by English total as the
  headline ratio;
- pins both Hugging Face tokenizer revisions;
- writes the corpus hash, package versions, preprocessing, bootstrap method,
  seed, and tokenizer revisions to `analysis_metadata.json`.

### Command

```bash
python partA/corrected_analysis.py
```

### Result

The run produced 21 rows: seven languages for each of three tokenizers.

| Tokenizer | Hindi | Kannada | Tamil | Telugu |
|---|---:|---:|---:|---:|
| GPT-2 | 7.42x | 13.58x | 15.54x | 12.97x |
| IndicBERTv2 reference | 1.17x | 1.10x | 1.05x | 1.06x |
| Qwen2.5 decoder | 4.42x | 6.92x | 6.11x | 6.99x |

All values are token-count ratios to English on the same sentence IDs. GPT-2
Hindi's paired-bootstrap 95% interval is [7.33, 7.51].

### Interpretation

Tokenizer vocabulary design materially affects fragmentation. However,
IndicBERTv2 is an encoder/MLM reference and cannot be swapped into an unrelated
generative model. Qwen2.5 also demonstrates that a large vocabulary or
"multilingual" label alone does not guarantee efficient Indic tokenization.

## 2026-09-05 - Part A4 recommendation revision

### Problem found in the AI draft

The initial memo called token ratios true cost multipliers, suggested swapping
an unrelated Indic tokenizer into GPT-2, and recommended a vocabulary-size
threshold contradicted by its own Qwen result.

### Revision

The memo now recommends evaluating complete model-and-tokenizer pairs and
labels the table as token-count ratios rather than measured GPU-cost ratios.
It contains the four required elements: corrected headline numbers, routing
recommendation, largest caveat, and one production monitoring metric. The memo
is 339 words including headings and table text.

### Current checkpoint

Parts A2, A3, and A4 have passed the independent revision. Parts B and C remain
unapproved. Personal local reruns and personal explanations are still required
before submission.

## 2026-09-05 - Part B capacity reconciliation audit

### Problems found in the AI draft

The first Part B answer mixed decimal GB and binary GiB and reported a
confusing 25-to-29 sequence range. Its binary branch contradicted itself: one
line stated 15,456,870,195 available bytes while the later division used
13,708,219,474. It also predicted a 69.2-second p95 latency after splitting 48
requests into two waves, although the log contains no measurement of that
queueing policy. Finally, it used an incorrect version-specific preemption
metric name and treated unique preempted sequences as necessarily equal to the
number of preemption events.

### Revision and command

I used the units printed in the supplied model spec consistently and rewrote
the analysis so each conclusion is generated from the untouched benchmark
log:

```bash
python partB/analyze_bench.py
```

The script now validates the input columns, checks that `reported_tok_s`
matches prompt-plus-generation throughput, derives output goodput two ways,
computes the KV bound, and writes source hashes to
`partB/analysis_summary.json`.

I then ran the integrated command below in the clean review environment; the
Part A audit, corrected tokenizer analysis, and Part B analysis all completed
successfully:

```bash
python run_all.py --skip-corpus
```

### Verified results

- KV cache: 114,688 bytes per token, exactly.
- Available KV memory under the stated assumptions: 12.08 GB.
- One 4096-token sequence: 469,762,048 bytes (448 MiB).
- Approximate capacity: 25 full-length sequences.
- Batch 24 matches the prediction: 0.93 KV use and zero preemptions.
- Batches 32 and 48 reach 0.97 KV use and preempt 7 and 23 sequences.
- Batch-24 long-prompt output goodput is 200.92 tok/s directly and 200.99
  tok/s by subtraction; the difference is only log rounding.
- At equal batch 16, long-prompt output goodput is 44.3% below short-prompt
  goodput, reversing the original report's conclusion.
- Capping concurrency at 24 predicts 200.92 output tok/s for 48 requests in
  two waves, 23.8% above the observed 162.31 tok/s. This remains a prediction
  until a new load test is run.

### Current checkpoint

Parts A2 through B4 have completed the evidence-level revision. Part C remains
unapproved. Personal local reruns and a live mock defense are still required
before submission.

## 2026-09-05 - Part C decision-memo audit

### Problems found in the AI draft

The first memo chose SFT using unmeasured claims such as less than five hours
of training, zero added latency, less than 100 MB of memory, and a 60-to-150 ms
rewriter penalty. It assumed access to a strong synthetic-data teacher despite
the no-external-API constraint. It also proposed using an automated judge for
four languages with no native reviewer, which could not establish whether the
output actually sounded natural. Finally, its Day-1 plan used 40 prompts but
claimed it could obtain 100 gold pairs.

### Revision

I changed the three-week recommendation to prompt engineering because it is
reversible and can be evaluated before spending the two-week GPU window. The
memo explicitly refuses to treat Hindi/Kannada evidence as approval for Tamil,
Telugu, Bengali, or Marathi. SFT remains a fallback only if the prompt-only
test fails.

The reviewer budget is:

```text
(3 weeks x 10 hours - 6 reserved hours) x 60 / 2 minutes
= 720 blinded comparisons
```

Day 1 uses 80 comparisons to choose between two prompt variants. The remaining
640 provide 320 held-out comparisons for Hindi and 320 for Kannada. The plan
therefore produces 1,400 reviewed responses from 680 unique prompts. A
120-token prompt cap adds 13.13 MiB of KV cache per active request on the Part
B model, or 315 MiB at 24 concurrent requests.

### Dead end caught during revision

An intermediate draft allocated 360 final comparisons to each language after
also spending 80 comparisons on Day 1. That would require 800 comparisons, not
the available 720. I corrected the final success gate to 320 held-out
comparisons per language; the Day-1 80 plus the final 640 now exactly match the
reviewer budget.

### Decision gates

- Success: at least 65% prompt preference in each reviewed language, with no
  more than 2% meaning-changing or unsafe responses.
- Kill by end of Day 5: below 55% preference in either language after 100
  comparisons per language, or more than 2% meaning/safety failures.
- Day 1: 20 Hindi and 20 Kannada prompts, three variants each, 80 blinded
  comparisons taking about 160 minutes.

No experiment outcome is recorded because the Day-1 experiment has not been
run. The memo describes a plan, not fabricated evidence.

### Current checkpoint

Parts A2 through C now have completed evidence-level revision. The next step is
the student's own local rerun, explanation practice, and live mock defense.

## 2026-09-05 - Final Part A1 corpus audit

### Hypothesis

The evaluation corpus should be reproducible from the included FLORES-200
archive without downloading data or silently changing sentence alignment.

### Problems found

The earlier builder did not check the archive against an expected hash, used a
broad tar extraction, and removed blank lines independently in each language.
That last behaviour could shift one language against the others if a source
file ever contained an empty row. The earlier README also described the domain
more narrowly than the supplied source documentation supported.

The assignment calls the English and Hindi starter samples line-parallel, but
the supplied files do not match by row. For example, English row 1 discusses
Bengaluru airport traffic while Hindi row 1 discusses liking morning tea. I
therefore retained those samples only for reproducing the aggregate v0 result
and used FLORES sentence IDs for aligned comparisons.

### Revision

`build_corpus.py` now checks the exact archive SHA-256, reads only seven named
regular files, requires equal line counts, rejects an empty aligned row, strips
only outer whitespace after that validation, and writes deterministic LF line
endings. It also creates `corpus_metadata.json` with source, preprocessing,
row count, languages, and every input/output hash.

### Commands and results

```bash
python partA/build_corpus.py
python verify_submission.py
```

All seven source files contain 1,012 rows and no blank rows. Two independent
builder runs produced the same corpus SHA-256:
`5dfb45774fae3ad78c7f850995661c41f43dbe4fcc76a215ff6cef6daaa16fdb`.
Two negative tests also passed: a deliberately blank aligned row and a
corrupted archive were both rejected.

I then ran the complete `python run_all.py` pipeline twice in the clean review
environment. The corpus, metadata, baseline, A2 table, A3 table and metadata,
and both Part B artifacts had identical SHA-256 hashes across the two runs.
`python verify_submission.py` passed after each run.

### Dead end and decision

An intermediate revision preserved leading/trailing spaces from four source
languages and produced a different hash. I rejected that version because it
would make accidental outer spaces part of the benchmark text. The final
version validates line positions first and then strips only outer whitespace.
Compared with the earlier checkpoint, all 1,012 parsed JSON records are
semantically identical; the remaining byte-level hash change is the deliberate
switch from platform-dependent CRLF to deterministic LF line endings.

### Final review status

The repository-level verifier checks A1 through C, but it is not a substitute
for the student's own rerun and oral explanation. No unrun experiment is
reported as a measured outcome.


## 2026-09-05 - Personal Windows verification

I ran `python run_all.py` and `python verify_submission.py` on Windows with
Python 3.13. The complete pipeline finished successfully, all generated
results matched the audited values, and the verifier reported
`ALL REPOSITORY CHECKS PASSED`.
