# Recommendation Memo - Tokenizer Audit

**To:** AI Product and Serving Leadership  
**Decision:** Do not use `REPORT_v0`'s flat 6x Indic cost assumption or route
traffic by language from that result.

## Corrected headline

I evaluated 1,012 aligned FLORES-200 sentences after consistent NFC
normalization while preserving case and punctuation. Values below are total
tokens for each language divided by English tokens for the same sentence IDs:

| Language | GPT-2 | IndicBERTv2 reference | Qwen2.5 decoder |
|---|---:|---:|---:|
| English | 1.00x | 1.00x | 1.00x |
| Hindi | 7.42x | 1.17x | 4.42x |
| Kannada | 13.58x | 1.10x | 6.92x |
| Tamil | 15.54x | 1.05x | 6.11x |
| Telugu | 12.97x | 1.06x | 6.99x |
| Bengali | 9.61x | 1.02x | 5.03x |
| Marathi | 7.86x | 1.05x | 4.62x |

The decision metric should be **mean tokens per aligned sentence, expressed as
a ratio to English**, because aligned sentences approximately hold meaning
constant. GPT-2 Hindi is 7.42x (95% paired-bootstrap CI: 7.33-7.51), not the
report's 5.89x word-based result.

## Routing recommendation

Tokenizer design drives much of the difference: the IndicBERTv2 reference is
near English token counts. But it is an encoder/MLM reference, not a drop-in
generative model or replacement tokenizer. A trained model must use its
compatible tokenizer.

Keep language-specific capacity estimates for the current GPT-2-tokenized
endpoint. For future routing, benchmark complete generative model-and-tokenizer
pairs on token count, answer quality, latency, and GPU-seconds before choosing.
Do not infer efficiency from vocabulary size or a "multilingual" label:
Qwen2.5 still measures 4.42x-6.99x for these Indic languages.

## Caveat and production check

FLORES is formal, clean, native-script text; it excludes production
romanization, code-mixing, typos, emojis, and conversational brevity. Token
count alone also does not equal GPU cost.

Monitor **matched-request token ratio**: mean total processed tokens per
successful request for each language divided by English within the same
request class. If the rolling ratio differs from this offline estimate by over
20%, replace the assumption with a production-weighted evaluation.

Reproducibility details are in `partA/results/analysis_metadata.json`.
