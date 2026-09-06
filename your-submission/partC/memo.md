# Decision Memo - Casual Indic Responses

**Recommendation - choose (c), prompt engineering, for the three-week review.**
It needs no training, is reversible, and fits the reviewer budget. Use SFT only
if it fails. Delay a rewriter until its latency and meaning errors are measured.
This does **not** approve a six-language production launch: only Hindi and
Kannada have native review.

## Explicit assumptions

1. The deployed model is Part B's 4.2B system; Day 1 tests whether it follows
   language-specific style instructions.
2. The fuller prompt variant is capped at 120 model tokens per request after
   tokenization.
3. One blinded comparison takes the reviewer 2 minutes.
4. The reviewer provides 30 hours; 6 are reserved for calibration, error
   analysis, and the launch review.
5. Tamil, Telugu, Bengali, and Marathi have no native review; automated checks
   cannot prove natural conversational style.

## Back-of-envelope arithmetic

**Reviewer throughput:** `(30 - 6) hours x 60 / 2 = 720` blinded comparisons:
360 Hindi and 360 Kannada. Day 1 uses 80; the remaining 640 cover 320 new
prompts per language.

**Evaluation data:** 680 unique Hindi/Kannada prompts produce 1,400 responses:
`40 x 3 variants + 640 x 2 variants`. Other-language smoke tests are not launch
evidence.

**Training and serving cost:** path (c) uses **0 GPU-hours for training** and
no external API. At one million requests, the prompt adds 120 million input
tokens. Using Part B's KV figure, it adds
`120 x 114,688 = 13,762,560 bytes` (13.13 MiB) of KV cache per active request,
or about 315 MiB at 24 concurrent requests. Prefill latency must be measured;
it is not estimated here. The A100 remains available for a fallback SFT pilot.

## Success metric - numeric launch gate

On 320 blinded comparisons **in each reviewed language**, the selected prompt
must be preferred for casualness and naturalness in at least **65%** of cases.
As a guardrail, meaning-changing or unsafe responses must be at most **2%**.
Passing applies only to Hindi and Kannada; the other four remain unapproved.

## Kill criterion

By **end of Day 5**, abandon prompt-only as the chosen path if, after 100
comparisons per language, its preference rate is below **55% in either Hindi
or Kannada**, or meaning/safety failures exceed **2%**. Use the remaining GPU
window for a small, separately evaluated LoRA/SFT pilot; do not silently weaken
the launch threshold.

## First experiment - Day 1

Select 20 Hindi and 20 Kannada prompts across four task categories. With
identical decoding settings, generate baseline, style-instruction, and
instruction-plus-two-example responses. Blind and randomize comparisons. The
reviewer completes 80 comparisons in `80 x 2 = 160 minutes`, recording
preference and meaning/safety failures. Use the result to select the Day-5
candidate; no outcome is claimed before the test.
