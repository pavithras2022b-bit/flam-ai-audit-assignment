#!/usr/bin/env python3
"""
run_all.py -- Master runner to execute the entire audit pipeline end-to-end.

Executes:
1. Baseline reproduction (partA/fertility_original.py -> partA/results/baseline.csv)
2. Multilingual parallel corpus builder (partA/build_corpus.py -> partA/data/eval_parallel.jsonl)
3. Script & metric audit suite (partA/audit_experiments.py -> partA/results/audit_deltas.csv)
4. Corrected multi-tokenizer analysis (partA/corrected_analysis.py -> partA/results/corrected_metrics.csv)
5. Capacity reconciliation bench analysis (partB/analyze_bench.py -> partB/derived_rows.csv)
"""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_name, command_args):
    print(f"\n=======================================================")
    print(f"STEP: {step_name}")
    print(f"COMMAND: {' '.join(command_args)}")
    print(f"=======================================================")
    res = subprocess.run(command_args, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"ERROR: Step '{step_name}' failed with return code {res.returncode}")
        sys.exit(res.returncode)
    print(f"SUCCESS: Step '{step_name}' completed.")


def main():
    parser = argparse.ArgumentParser(description="Run complete audit pipeline.")
    parser.add_argument(
        "--skip-corpus", action="store_true", help="Skip downloading FLORES corpus if already present."
    )
    args = parser.parse_args()

    # Step 1: Baseline reproduction
    sample_eng = os.path.join(BASE_DIR, "..", "starter_kit", "starter_kit", "corpus_sample", "eng_sample.txt")
    sample_hin = os.path.join(BASE_DIR, "..", "starter_kit", "starter_kit", "corpus_sample", "hin_sample.txt")
    baseline_out = os.path.join(BASE_DIR, "partA", "results", "baseline.csv")
    
    os.makedirs(os.path.dirname(baseline_out), exist_ok=True)
    print("\n--- Running Baseline Reproduction ---")
    with open(baseline_out, "w", encoding="utf-8") as f:
        res = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "partA", "fertility_original.py"),
             "--corpus", f"eng={sample_eng}", "--corpus", f"hin={sample_hin}", "--tokenizer", "gpt2"],
            stdout=f, stderr=subprocess.PIPE, text=True
        )
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        print("ERROR: Baseline reproduction failed.", file=sys.stderr)
        sys.exit(res.returncode)
    print("Saved baseline output to partA/results/baseline.csv")

    # Step 2: Build corpus
    if not args.skip_corpus or not os.path.exists(os.path.join(BASE_DIR, "partA", "data", "eval_parallel.jsonl")):
        run_step("Build FLORES Corpus", [sys.executable, os.path.join(BASE_DIR, "partA", "build_corpus.py")])
    else:
        print("\n--- Skipping corpus build (already exists) ---")

    # Step 3: Audit experiments
    run_step("Audit Isolating Experiments", [sys.executable, os.path.join(BASE_DIR, "partA", "audit_experiments.py")])

    # Step 4: Corrected analysis
    run_step("Corrected Multi-Tokenizer Analysis", [sys.executable, os.path.join(BASE_DIR, "partA", "corrected_analysis.py")])

    # Step 5: Capacity bench analysis
    run_step("Capacity Reconciliation Analysis", [sys.executable, os.path.join(BASE_DIR, "partB", "analyze_bench.py")])

    print("\n" + "*" * 80)
    print("ALL AUDIT STEPS COMPLETED SUCCESSFULLY!")
    print("All output CSVs and tables have been generated under your-submission/")
    print("*" * 80 + "\n")


if __name__ == "__main__":
    main()
