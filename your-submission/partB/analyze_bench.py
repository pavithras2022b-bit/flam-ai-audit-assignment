#!/usr/bin/env python3
"""Reproduce every number used in the Part B capacity reconciliation.

The script keeps three quantities separate: total processed throughput
(prompt + generated tokens), prompt-prefill throughput, and generated-output
goodput. It also computes the model-spec KV bound and a labelled prediction.
"""

import hashlib
import json
import os

import pandas as pd


PART_B_DIR = os.path.dirname(os.path.abspath(__file__))
BENCH_DIR = os.path.abspath(
    os.path.join(
        PART_B_DIR,
        "..",
        "..",
        "starter_kit",
        "starter_kit",
        "bench",
    )
)
BENCH_LOG = os.path.join(BENCH_DIR, "bench_log.csv")
MODEL_SPEC = os.path.join(BENCH_DIR, "model_spec.md")
OUTPUT_CSV = os.path.join(PART_B_DIR, "derived_rows.csv")
OUTPUT_SUMMARY = os.path.join(PART_B_DIR, "analysis_summary.json")

# Values copied from bench/model_spec.md. The spec writes memory quantities in
# GB, so capacity arithmetic consistently uses 1 GB = 10^9 bytes.
LAYERS = 28
KV_HEADS = 8
HEAD_DIM = 128
KV_ELEMENT_BYTES = 2  # fp16
KEY_AND_VALUE = 2
PARAMETERS = 4_200_000_000
WEIGHT_ELEMENT_BYTES = 2  # fp16
GPU_BYTES = 24_000_000_000
GPU_MEMORY_UTILIZATION = 0.92
NON_KV_OVERHEAD_BYTES = 1_600_000_000
MAX_MODEL_LEN = 4096


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capacity_from_spec():
    """Return the exact per-token KV size and approximate sequence bound."""
    kv_bytes_per_token = (
        KEY_AND_VALUE
        * LAYERS
        * KV_HEADS
        * HEAD_DIM
        * KV_ELEMENT_BYTES
    )
    usable_gpu_bytes = int(GPU_BYTES * GPU_MEMORY_UTILIZATION)
    weight_bytes = PARAMETERS * WEIGHT_ELEMENT_BYTES
    available_kv_bytes = (
        usable_gpu_bytes - weight_bytes - NON_KV_OVERHEAD_BYTES
    )
    kv_bytes_per_full_sequence = kv_bytes_per_token * MAX_MODEL_LEN
    maximum_full_sequences = available_kv_bytes // kv_bytes_per_full_sequence

    return {
        "kv_bytes_per_token": kv_bytes_per_token,
        "kv_kib_per_token": kv_bytes_per_token / 1024,
        "usable_gpu_bytes": usable_gpu_bytes,
        "weight_bytes": weight_bytes,
        "non_kv_overhead_bytes": NON_KV_OVERHEAD_BYTES,
        "available_kv_bytes": available_kv_bytes,
        "kv_bytes_per_4096_sequence": kv_bytes_per_full_sequence,
        "kv_mib_per_4096_sequence": (
            kv_bytes_per_full_sequence / (1024**2)
        ),
        "maximum_4096_token_sequences": int(maximum_full_sequences),
        "predicted_kv_util_at_24": (
            24 * kv_bytes_per_full_sequence / available_kv_bytes
        ),
        "predicted_kv_util_at_25": (
            25 * kv_bytes_per_full_sequence / available_kv_bytes
        ),
    }


def load_and_derive():
    df = pd.read_csv(BENCH_LOG)
    required = {
        "batch_size",
        "prompt_len",
        "gen_len",
        "num_requests",
        "wall_clock_s",
        "reported_tok_s",
        "ttft_ms_p50",
        "itl_ms_p50",
        "e2e_ms_p95",
        "preempted_seqs",
        "kv_cache_util",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"bench_log.csv is missing columns: {sorted(missing)}")
    if df.empty or (df["wall_clock_s"] <= 0).any():
        raise ValueError("Benchmark log must contain positive-duration rows")
    if not (df["batch_size"] == df["num_requests"]).all():
        raise ValueError("This analysis expects batch_size == num_requests")

    df["total_prompt_tokens"] = df["num_requests"] * df["prompt_len"]
    df["total_generation_tokens"] = df["num_requests"] * df["gen_len"]
    df["total_processed_tokens"] = (
        df["total_prompt_tokens"] + df["total_generation_tokens"]
    )
    df["implied_total_tok_s"] = (
        df["total_processed_tokens"] / df["wall_clock_s"]
    )
    df["reported_total_diff_tok_s"] = (
        df["reported_tok_s"] - df["implied_total_tok_s"]
    ).abs()
    df["prompt_prefill_tok_s"] = (
        df["total_prompt_tokens"] / df["wall_clock_s"]
    )
    df["output_goodput_direct_tok_s"] = (
        df["total_generation_tokens"] / df["wall_clock_s"]
    )
    df["output_goodput_from_reported_tok_s"] = (
        df["reported_tok_s"] - df["prompt_prefill_tok_s"]
    )
    df["goodput_method_diff_tok_s"] = (
        df["output_goodput_direct_tok_s"]
        - df["output_goodput_from_reported_tok_s"]
    ).abs()
    df["prompt_share_pct"] = (
        100 * df["total_prompt_tokens"] / df["total_processed_tokens"]
    )
    df["preempted_request_pct"] = (
        100 * df["preempted_seqs"] / df["num_requests"]
    )

    # reported_tok_s is rounded to one decimal place, so derived methods are
    # expected to agree within a small rounding tolerance.
    if df["reported_total_diff_tok_s"].max() >= 0.25:
        raise AssertionError(
            "reported_tok_s is not total processed tokens/s within tolerance"
        )
    if df["goodput_method_diff_tok_s"].max() >= 0.25:
        raise AssertionError("The two output-goodput methods disagree")
    return df


def exactly_one_row(df, prompt_len, batch_size):
    selected = df[
        (df["prompt_len"] == prompt_len)
        & (df["batch_size"] == batch_size)
    ]
    if len(selected) != 1:
        raise ValueError(
            f"Expected one row for prompt={prompt_len}, batch={batch_size}"
        )
    return selected.iloc[0]


def build_summary(df, capacity):
    short16 = exactly_one_row(df, 512, 16)
    long16 = exactly_one_row(df, 3584, 16)
    long24 = exactly_one_row(df, 3584, 24)
    long32 = exactly_one_row(df, 3584, 32)
    long48 = exactly_one_row(df, 3584, 48)

    predicted_wall_s = 2 * long24["wall_clock_s"]
    predicted_goodput = (
        long48["total_generation_tokens"] / predicted_wall_s
    )
    observed_batch48_goodput = long48["output_goodput_direct_tok_s"]

    summary = {
        "source_files": {
            "model_spec_sha256": file_sha256(MODEL_SPEC),
            "bench_log_sha256": file_sha256(BENCH_LOG),
        },
        "capacity_from_model_spec": capacity,
        "log_check": {
            "batch_24": {
                "kv_cache_util": long24["kv_cache_util"],
                "preempted_seqs": int(long24["preempted_seqs"]),
            },
            "batch_32": {
                "kv_cache_util": long32["kv_cache_util"],
                "preempted_seqs": int(long32["preempted_seqs"]),
            },
            "batch_48": {
                "kv_cache_util": long48["kv_cache_util"],
                "preempted_seqs": int(long48["preempted_seqs"]),
            },
        },
        "b2_anomaly": {
            "reported_tok_s_batch_24": long24["reported_tok_s"],
            "reported_tok_s_batch_32": long32["reported_tok_s"],
            "reported_tok_s_batch_48": long48["reported_tok_s"],
            "batch_24_to_32_change_pct": 100
            * (long32["reported_tok_s"] / long24["reported_tok_s"] - 1),
            "batch_24_to_48_change_pct": 100
            * (long48["reported_tok_s"] / long24["reported_tok_s"] - 1),
        },
        "b3_goodput": {
            "batch_24_long_direct_tok_s": long24[
                "output_goodput_direct_tok_s"
            ],
            "batch_24_long_from_reported_tok_s": long24[
                "output_goodput_from_reported_tok_s"
            ],
            "batch_16_short_tok_s": short16[
                "output_goodput_direct_tok_s"
            ],
            "batch_16_long_tok_s": long16[
                "output_goodput_direct_tok_s"
            ],
            "batch_16_long_vs_short_change_pct": 100
            * (
                long16["output_goodput_direct_tok_s"]
                / short16["output_goodput_direct_tok_s"]
                - 1
            ),
            "batch_48_long_tok_s": observed_batch48_goodput,
        },
        "cap_24_prediction_for_48_requests": {
            "assumption": (
                "Two sequential 24-request waves reproduce the measured "
                "batch-24 row; this is a prediction, not a measured run."
            ),
            "predicted_wall_clock_s": predicted_wall_s,
            "predicted_output_goodput_tok_s": predicted_goodput,
            "predicted_goodput_change_vs_batch_48_pct": 100
            * (predicted_goodput / observed_batch48_goodput - 1),
        },
    }

    if capacity["maximum_4096_token_sequences"] != 25:
        raise AssertionError("Unexpected full-length sequence capacity")
    if int(long24["preempted_seqs"]) != 0:
        raise AssertionError("Batch 24 should be the last clean long row")
    if not (
        int(long32["preempted_seqs"]) == 7
        and int(long48["preempted_seqs"]) == 23
    ):
        raise AssertionError("Long-context preemption evidence changed")
    return summary


def print_summary(summary):
    capacity = summary["capacity_from_model_spec"]
    anomaly = summary["b2_anomaly"]
    goodput = summary["b3_goodput"]
    prediction = summary["cap_24_prediction_for_48_requests"]

    print("Part B verified summary")
    print(f"KV bytes/token: {capacity['kv_bytes_per_token']:,}")
    print(
        "Approx. concurrent 4096-token sequences: "
        f"{capacity['maximum_4096_token_sequences']}"
    )
    print(
        "Long reported tok/s (batch 24 -> 32 -> 48): "
        f"{anomaly['reported_tok_s_batch_24']:.1f} -> "
        f"{anomaly['reported_tok_s_batch_32']:.1f} -> "
        f"{anomaly['reported_tok_s_batch_48']:.1f}"
    )
    print(
        "Batch-24 long output goodput, direct/from reported: "
        f"{goodput['batch_24_long_direct_tok_s']:.2f} / "
        f"{goodput['batch_24_long_from_reported_tok_s']:.2f} tok/s"
    )
    print(
        "Predicted cap-24 goodput for 48 requests: "
        f"{prediction['predicted_output_goodput_tok_s']:.2f} tok/s "
        f"({prediction['predicted_goodput_change_vs_batch_48_pct']:+.1f}%)"
    )


def main():
    capacity = capacity_from_spec()
    df = load_and_derive()
    summary = build_summary(df, capacity)

    df.to_csv(OUTPUT_CSV, index=False, float_format="%.6f")
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")

    print_summary(summary)
    print(f"Saved {len(df)} rows to {OUTPUT_CSV}")
    print(f"Saved verification summary to {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
