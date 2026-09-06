# Part A2 - Evidence-Backed Audit Findings

This document audits `fertility.py` one choice at a time. All commands below
are run from `your-submission/`. The generated evidence table is
`partA/results/audit_deltas.csv`.

## Baseline reproduction

Command:

```bash
python partA/fertility_original.py \
  --corpus eng=../starter_kit/starter_kit/corpus_sample/eng_sample.txt \
  --corpus hin=../starter_kit/starter_kit/corpus_sample/hin_sample.txt \
  --tokenizer gpt2
```

Result: English fertility `1.27`, Hindi fertility `7.45`, and reported
Hindi/English ratio `5.89x`. This reproduces `REPORT_v0.md` before any audit
change.

## FLAW-1 - Literal-space splitting counts empty strings

Command:

```bash
python partA/audit_experiments.py --experiment split_spaces
```

Before/after: the double-spaced line is counted as 8 items by `split(" ")`
and 7 words by `split()`, changing its fertility from `1.2500` to `1.4286`.
Across the full starter sample, the Hindi/English ratio changes from `5.8871`
to `5.9221`.

Why this proves the claim: changing only the whitespace-splitting operation
changes the result; the original method understates the sample ratio by 0.59%.

## FLAW-2 - Lowercasing does not represent raw serving text

Command:

```bash
python partA/audit_experiments.py --experiment lowercase
```

Before/after: on the starter sample, English changes from 96 raw tokens to 99
lowercased tokens, while Hindi remains 459 tokens. The reported ratio is
`5.8871` with lowercasing and `6.0590` without it.

Full-corpus check: on FLORES, English changes from 27,044 raw tokens to 27,994
lowercased tokens; Hindi changes from 200,467 to 200,475.

Why this proves the claim: the preprocessing changes the operational number
asymmetrically. A serving-cost analysis must tokenize the same text form that
the production model receives. If production intentionally lowercases all
input, this becomes a documented preprocessing choice rather than a flaw.

## FLAW-3 - Mean of line ratios is not the pooled corpus ratio

Command:

```bash
python partA/audit_experiments.py --experiment macro_average
```

Before/after: with whitespace handling held fixed, averaging line-level
fertilities gives `5.922121`; dividing total tokens by total words gives
`5.928465`.

Why this proves the claim: the aggregation choice changes the result by 0.11%.
The effect is small on this sample, and the audit reports it as small.

## FLAW-4 - The label "character" is ambiguous

Command:

```bash
python partA/audit_experiments.py --experiment character_unit
```

Before/after: the Hindi/English ratio is `6.9985` tokens per Unicode code point
and `10.8570` tokens per user-visible grapheme cluster.

Why this proves the claim: Python `len(text)` measures Unicode code points, not
user-visible characters. More importantly, neither character unit holds
meaning constant across languages, so `tok/char` cannot independently confirm
a serving-cost claim.

## FLAW-5 - Per-word comparison does not hold meaning constant

Command:

```bash
python partA/audit_experiments.py --experiment parallel_denominator
```

Before/after: on the same 1,012 aligned FLORES sentences with the same GPT-2
tokenizer, the Hindi/English ratio is `6.3309` per whitespace word and
`7.4126` per aligned sentence.

Why this proves the claim: only the denominator changed. The word-based number
is 14.59% below the aligned-sentence number because a word is not a comparable
amount of meaning across languages.

## Verified controls - suspicious but not bugs

Commands:

```bash
python partA/audit_experiments.py --experiment nfc_control
python partA/audit_experiments.py --experiment random_seed_control
```

- NFC normalization changes zero tokens in the v0 starter sample, so it does
  not alter the reported v0 result. It changes the seven-language FLORES total
  by 0.081%, so the corrected analysis must still apply it consistently and
  document the choice.
- Changing the random seed produces the identical ratio `5.887148` because
  `fertility.py` never performs a random operation. The seed is harmless dead
  code.

## Supplied starter-data alignment note - not a script flaw

Although the assignment description calls the tiny English and Hindi files
line-parallel, the supplied copy is not consistently aligned. Check the first
row directly:

```bash
python -c "from pathlib import Path; p=Path('../starter_kit/starter_kit/corpus_sample'); print((p/'eng_sample.txt').read_text(encoding='utf-8').splitlines()[0]); print((p/'hin_sample.txt').read_text(encoding='utf-8').splitlines()[0])"
```

The English row is about Bengaluru airport traffic; the Hindi row begins
`मुझे सुबह की चाय बहुत पसंद है।`, which is about liking morning tea. Therefore
I reproduce the v0 aggregate numbers from these files but do not use their row
positions as equal-meaning units. The FLORES corpus supplies the aligned rows
used for sentence-level comparison.

## Scope of the conclusion

The v0 value `5.89x` is not a valid general cost multiplier: it comes from ten
non-parallel sample lines, an English-centric tokenizer, and denominators that
do not hold meaning constant. On the larger aligned FLORES corpus, GPT-2's
Hindi/English token-count ratio is `7.41x`. This does not mean every production
Hindi request costs exactly 7.41 times an English request; it is a
token-count result for one tokenizer and one formal translation corpus.
