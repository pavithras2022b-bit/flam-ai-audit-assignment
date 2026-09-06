# Simple Audit Defense Guide

This file is a study guide, not evidence. Use it to understand the work, then
explain the answers in your own words.

## The whole assignment in one sentence

The old report confused tokenizer measurements and serving throughput with
real product cost; this audit rebuilt the evidence, found the actual capacity
limit, and replaced confident guesses with measured numbers and testable
recommendations.

## Ten numbers to understand

| Number | What it means |
|---:|---|
| 1,012 x 7 | Aligned FLORES sentences x languages in A1 |
| 5.89x | Old tiny-sample Hindi/English word-based ratio |
| 7.42x | GPT-2 Hindi/English tokens per aligned sentence |
| 1.17x | IndicBERT reference Hindi/English token ratio |
| 114,688 bytes | KV cache needed per token in Part B |
| 25 | Approximate full 4096-token sequences that fit |
| 200.92 tok/s | Honest batch-24 long-prompt output goodput |
| 23.8% | Predicted goodput gain from serving 48 requests as two waves of 24 |
| 720 | Total Part C blinded reviewer comparisons |
| 65% / 55% / 2% | Success / kill / meaning-safety thresholds in Part C |

## Seven terms in simple language

- **Token:** a piece of text the model processes.
- **Tokenizer:** the rulebook that breaks text into tokens.
- **Denominator:** what the token count is divided by. It changes what the
  metric means.
- **Aligned sentence:** the same meaning translated into each language.
- **KV cache:** GPU memory storing attention information for tokens already
  processed.
- **Goodput:** useful generated output tokens per second, not prompt tokens.
- **Preemption:** pausing a request because the serving engine lacks capacity.

## Likely questions and short answers

### Why not use tokens per word for routing?

A word is not the same amount of meaning across languages. An aligned sentence
approximately holds meaning constant, so total tokens for the same sentence
IDs is the most defensible offline comparison.

### Does 7.42x mean Hindi costs exactly 7.42x more?

No. It is a token-count ratio for GPT-2 on formal FLORES text. Real cost also
depends on traffic mix, output length, batching, latency, and hardware.

### Why did you test three tokenizers?

To show that the result depends heavily on tokenizer design. GPT-2 fragments
Indic scripts severely, while the Indic-aware reference is near English. But
IndicBERT is an encoder reference and cannot be swapped into an unrelated
generative model; complete model-tokenizer pairs must be evaluated.

### What was the harmless suspicious code?

`random.seed(1337)` looks important, but the original script uses no random
operation. Changing the seed leaves the ratio exactly 5.887148. NFC also leaves
the tiny v0 sample unchanged, although it matters slightly on the larger set.

### Why did you not trust the tiny starter files as aligned sentences?

The supplied first English row discusses Bengaluru airport traffic, while the
first Hindi row discusses liking morning tea. I reproduce their aggregate v0
numbers, but I use FLORES for equal-meaning sentence comparisons.

### Re-derive KV bytes per token.

```text
2 for key+value x 28 layers x 8 KV heads x 128 head dimension x 2 fp16 bytes
= 114,688 bytes/token
```

### Re-derive the 25-sequence limit.

```text
Usable GPU memory = 24 GB x 0.92 = 22.08 GB
Minus weights     = 4.2B x 2 bytes = 8.40 GB
Minus overhead    = 1.60 GB
KV available      = 12.08 GB

One full request  = 4096 x 114,688 = 469,762,048 bytes
12,080,000,000 / 469,762,048 = 25.71, so about 25 fit
```

The log supports this: batch 24 has 0.93 KV use and zero preemptions; batches
32 and 48 reach 0.97 and preempt 7 and 23 sequences.

### What exactly was wrong with `reported_tok_s`?

It counts prompt plus generated tokens. For the long batch-24 row:

```text
Useful output = 24 x 512 / 61.16 = 200.92 generated tok/s
```

The reported 1607.4 tok/s is mostly the 3,584-token prompt prefill, so it is not
output goodput.

### Why choose prompt engineering in Part C?

The three-week constraint is dominated by reviewer coverage, not GPU time.
Prompting is reversible and measurable immediately. Only Hindi and Kannada
have native review, so the memo refuses to claim that the other four languages
are ready.

### What evidence is still missing?

The Part B concurrency-cap improvement is predicted, not load-tested. The Part
C Day-1 experiment has not been run. Production tokenizer ratios and natural
style in four languages also remain unmeasured.

## Counterfactuals they may ask

| Change | Expected result, with other assumptions fixed |
|---|---|
| KV cache fp16 to fp8 | 57,344 bytes/token; about 51 full sequences |
| Context 4096 to 2048 | KV per request halves; about 51 sequences |
| KV heads 8 to 24 | KV triples to 344,064 bytes/token; about 8 sequences |
| GPU utilization 0.92 to 0.95 | KV budget becomes 12.8 GB; about 27 sequences |
| Part C prompt 120 to 60 tokens | Added KV overhead halves to 6.56 MiB/request |
| Production has romanized/code-mixed text | Offline ratios may change; rerun on matched production samples |

Always say which assumptions are being held fixed. A prediction is not a
measurement.

## Commands to practise

From `your-submission/`:

```bash
python partA/build_corpus.py
python partA/audit_experiments.py --experiment split_spaces
python partA/audit_experiments.py --experiment parallel_denominator
python partA/corrected_analysis.py --tokenizer gpt2
python partB/analyze_bench.py
python run_all.py
python verify_submission.py
```

On Windows PowerShell, first create and activate the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Thirty-minute mock defense

1. **Minutes 0-5:** explain the one-sentence story and A1 corpus.
2. **Minutes 5-12:** explain two A2 flaws, one harmless control, and why aligned
   sentences are the headline denominator.
3. **Minutes 12-20:** re-derive 114,688 bytes, 25 sequences, and 200.92 tok/s.
4. **Minutes 20-25:** defend prompt-only, 720 comparisons, and the kill rule.
5. **Minutes 25-30:** run one command and change one CLI value live.

## Final checklist for you

- [ ] Unzip the submission candidate into a fresh folder.
- [ ] Install `requirements.txt` in a fresh virtual environment.
- [ ] Run `python run_all.py` and `python verify_submission.py` yourself.
- [ ] Add your own dated result and any setup issue to `NOTEBOOK.md`.
- [ ] Explain the ten numbers above without reading them word-for-word.
- [ ] Practise one counterfactual and one small code edit.
- [ ] Tick the `AI_USAGE.md` boxes only after you genuinely complete them.
- [ ] Do not claim the Part B prediction or Part C plan was experimentally run.

If you do not know an answer, say: **"The supplied data does not establish
that. Here is the smallest experiment I would run."** That is stronger than a
confident guess.
