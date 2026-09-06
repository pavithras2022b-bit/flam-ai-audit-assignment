# Part B - Capacity Reconciliation

Reproduce every derived value with:

```bash
python partB/analyze_bench.py
```

The script uses constants transcribed from the untouched `model_spec.md`, reads
the untouched `bench_log.csv`, writes `derived_rows.csv`, and checks the key
claims before writing `analysis_summary.json`. The summary stores hashes of
both source files so a changed input cannot be mistaken for the audited input.

## B1 - KV-cache capacity

### Exact bytes per token

For every token, each layer stores one key and one value for each KV head:

```text
2 (K and V) x 28 layers x 8 KV heads x 128 values/head x 2 bytes/fp16
= 114,688 bytes/token
= 112 KiB/token
```

The 8 KV heads must be used, not the 24 query heads.

### Approximate concurrent 4096-token sequences

I use the GB units printed in the spec consistently (`1 GB = 10^9 bytes`):

```text
Configured usable GPU memory = 24,000,000,000 x 0.92
                             = 22,080,000,000 bytes
FP16 model weights           = 4,200,000,000 x 2
                             =  8,400,000,000 bytes
Non-KV runtime overhead      =  1,600,000,000 bytes
Available KV memory          = 12,080,000,000 bytes

KV per full sequence         = 114,688 x 4096
                             = 469,762,048 bytes (448 MiB)

Maximum full sequences       = floor(12,080,000,000 / 469,762,048)
                             = floor(25.71)
                             = approximately 25 sequences
```

This is approximate because the stated 1.6 GB overhead is approximate and a
real allocator reserves memory in blocks.

### Check against the log

The calculation predicts 93.33% KV use at 24 sequences and 97.22% at 25.
The long-prompt log shows 0.93 utilization with no preemption at batch 24.
At batches 32 and 48, utilization stays near 0.97 while 7 and 23 sequences,
respectively, are preempted. The model-spec estimate therefore agrees closely
with the observed boundary.

## B2 - Long-context anomaly and mechanism

| Batch | Reported total tok/s | Output goodput | Wall time | KV use | Preempted | p95 E2E |
|---:|---:|---:|---:|---:|---:|---:|
| 24 | 1607.4 | 200.92 | 61.16 s | 0.93 | 0 | 69.22 s |
| 32 | 1384.0 | 172.99 | 94.71 s | 0.97 | 7 | 97.47 s |
| 48 | 1298.5 | 162.31 | 151.41 s | 0.97 | 23 | 105.43 s |

The anomaly begins after batch 24: adding requests makes reported throughput
fall 13.9% at batch 32 and 19.2% at batch 48. This is not ordinary scaling.
The specific rows show the mechanism: the cache reaches its practical limit,
the scheduler preempts sequences, and the extra recovery/scheduling work
reduces throughput while latency rises. The log proves preemption; the exact
recovery mode (recompute or swap) is not recorded, so I do not claim which one
was configured.

**Proposed change:** set the long-context concurrency limit to 24 sequences
(`max_num_seqs = 24` in a vLLM-style deployment). For
the same 48 requests, two sequential waves matching the measured batch-24 row
would take approximately `2 x 61.16 = 122.32 s` and deliver
`24,576 / 122.32 = 200.92` generated tok/s. That is a predicted 23.8% goodput
increase over the observed batch-48 value of 162.31 tok/s. This prediction
assumes both waves reproduce the batch-24 measurement; it must be confirmed by
one new load test. I do not predict p95 latency because queueing policy would
determine it.

## B3 - The misread column and honest goodput

The misread column is `reported_tok_s`. It counts **prompt plus generated
tokens**, not only useful generated output. The report's own batch-16 rows
demonstrate this:

```text
Short: 16 x (512 + 256) / 13.91 = 883.39 total tok/s ~= reported 883.2
Long:  16 x (3584 + 512) / 49.97 = 1311.51 total tok/s ~= reported 1311.4
```

The long row appears faster because every request includes 3,584 prompt tokens
that the counter also credits as throughput.

For the batch-24 long-prompt row, honest output goodput is 200.92 tok/s by the
direct method:

```text
24 requests x 512 generated tokens / 61.16 s = 200.92 generated tok/s
```

An independent subtraction gives the same answer within log rounding:

```text
Prompt throughput = 24 x 3584 / 61.16 = 1406.41 tok/s
Output goodput     = 1607.4 - 1406.41 = 200.99 generated tok/s
```

The honest report should say that, at the same batch 16, output goodput falls
from 294.46 tok/s for the short prompt to 163.94 tok/s for the long prompt - a
44.3% decrease. The long-prompt batch-48 row delivers only 162.31 generated
tok/s, not approximately 3200 tok/s. Capacity planning must separate prompt
prefill throughput from generated-output goodput.

## B4 - One production counter

I would pull the scheduler's cumulative preemption counter. In vLLM this is
documented as [`vllm:num_preemptions`](https://docs.vllm.ai/en/stable/usage/metrics/)
(Prometheus may expose the counter with a `_total` suffix). For isolated runs,
I expect a delta of 0 at batch 24, at least 7 at batch 32, and at least 23 at
batch 48. The latter two are minimums because `preempted_seqs` counts unique
sequences, while one sequence could be preempted more than once. A rising
counter exactly when KV utilization reaches about 0.97 would confirm the
proposed KV-saturation-to-preemption mechanism; a zero delta would refute it.
