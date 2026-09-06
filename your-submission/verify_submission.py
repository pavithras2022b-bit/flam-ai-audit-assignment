#!/usr/bin/env python3
"""Fail-fast structural and arithmetic checks for the submission repository.

Run this after ``python run_all.py``. It does not replace understanding or the
live defense; it catches missing files, stale hashes, row-count drift, and
contradictions between generated artifacts.
"""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STARTER = ROOT.parent / "starter_kit" / "starter_kit"
LANGUAGES = {
    "eng_Latn",
    "hin_Deva",
    "kan_Knda",
    "tam_Taml",
    "tel_Telu",
    "ben_Beng",
    "mar_Deva",
}


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require_files():
    required = (
        "README.md",
        "NOTEBOOK.md",
        "AI_USAGE.md",
        "DEFENSE_GUIDE.md",
        "partA/build_corpus.py",
        "partA/data/eval_parallel.jsonl",
        "partA/data/corpus_metadata.json",
        "partA/AUDIT_FINDINGS.md",
        "partA/results/audit_deltas.csv",
        "partA/corrected_analysis.py",
        "partA/results/corrected_metrics.csv",
        "partA/results/analysis_metadata.json",
        "partA/recommendation_memo.md",
        "partB/analyze_bench.py",
        "partB/calculations.md",
        "partB/derived_rows.csv",
        "partB/analysis_summary.json",
        "partC/memo.md",
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"Missing required files: {missing}"
    print("PASS files: required deliverables are present")


def verify_a1():
    metadata_path = ROOT / "partA/data/corpus_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    corpus_path = ROOT / metadata["output_path"]
    archive_path = ROOT / metadata["archive_path"]

    assert file_sha256(archive_path) == metadata["archive_sha256"]
    assert file_sha256(corpus_path) == metadata["output_sha256"]
    assert set(metadata["languages"]) == LANGUAGES
    assert metadata["parallel_sentences"] == 1012

    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(records) == 1012
    assert [row["sentence_id"] for row in records] == list(range(1, 1013))
    expected_keys = LANGUAGES | {"sentence_id"}
    for row in records:
        assert set(row) == expected_keys
        for language in LANGUAGES:
            assert row[language]
            assert row[language] == row[language].strip()

    raw_dir = ROOT / "partA/data/raw/flores200_dataset/devtest"
    for language in LANGUAGES:
        raw_path = raw_dir / f"{language}.devtest"
        item = metadata["language_files"][language]
        assert raw_path.is_file()
        assert len(raw_path.read_text(encoding="utf-8").splitlines()) == 1012
        assert file_sha256(raw_path) == item["sha256"]
    print("PASS A1: 1,012 aligned rows, 7 languages, and all hashes match")


def verify_a2():
    rows = read_csv(ROOT / "partA/results/audit_deltas.csv")
    expected = {
        "FLAW-1",
        "FLAW-2",
        "FLAW-3",
        "FLAW-4",
        "FLAW-5",
        "CONTROL-1",
        "CONTROL-2",
    }
    assert {row["experiment_id"] for row in rows} == expected
    for row in rows:
        assert row["exact_command"].startswith("python partA/")
        assert row["evidence"] and row["conclusion"]
    print("PASS A2: 5 measured flaws and 2 measured controls are complete")


def verify_a3_a4():
    rows = read_csv(ROOT / "partA/results/corrected_metrics.csv")
    assert len(rows) == 21
    assert {row["tokenizer_key"] for row in rows} == {
        "gpt2",
        "indicbert",
        "qwen2.5",
    }
    assert {row["language_code"] for row in rows} == LANGUAGES
    for row in rows:
        ratio = float(row["sentence_ratio_to_english"])
        low = float(row["sentence_ratio_ci95_low"])
        high = float(row["sentence_ratio_ci95_high"])
        assert low <= ratio <= high
        if row["language_code"] == "eng_Latn":
            assert ratio == 1.0

    metadata = json.loads(
        (ROOT / "partA/results/analysis_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    corpus_path = ROOT / "partA/data/eval_parallel.jsonl"
    assert metadata["corpus_sha256"] == file_sha256(corpus_path)
    assert metadata["parallel_sentences"] == 1012
    assert metadata["bootstrap"]["samples"] == 1000
    assert metadata["bootstrap"]["seed"] == 42

    memo = (ROOT / "partA/recommendation_memo.md").read_text(encoding="utf-8")
    assert len(memo.split()) <= 500
    for heading in (
        "Corrected headline",
        "Routing recommendation",
        "Caveat and production check",
    ):
        assert heading in memo
    print("PASS A3/A4: 21 result rows, matching metadata, and concise memo")


def verify_b():
    rows = read_csv(ROOT / "partB/derived_rows.csv")
    summary = json.loads(
        (ROOT / "partB/analysis_summary.json").read_text(encoding="utf-8")
    )
    assert len(rows) == 13
    assert summary["source_files"]["model_spec_sha256"] == file_sha256(
        STARTER / "bench/model_spec.md"
    )
    assert summary["source_files"]["bench_log_sha256"] == file_sha256(
        STARTER / "bench/bench_log.csv"
    )
    capacity = summary["capacity_from_model_spec"]
    assert capacity["kv_bytes_per_token"] == 114688
    assert capacity["maximum_4096_token_sequences"] == 25
    goodput = summary["b3_goodput"]
    assert round(goodput["batch_24_long_direct_tok_s"], 2) == 200.92
    assert round(goodput["batch_24_long_from_reported_tok_s"], 2) == 200.99
    calculations = (ROOT / "partB/calculations.md").read_text(
        encoding="utf-8"
    )
    for heading in ("B1", "B2", "B3", "B4"):
        assert heading in calculations
    print("PASS B: capacity, anomaly, goodput, and source hashes agree")


def verify_c_and_disclosures():
    memo = (ROOT / "partC/memo.md").read_text(encoding="utf-8")
    assert len(memo.split()) <= 500
    for label in (
        "Recommendation",
        "Explicit assumptions",
        "Back-of-envelope arithmetic",
        "Success metric",
        "Kill criterion",
        "First experiment - Day 1",
    ):
        assert label in memo
    assert "no outcome is claimed" in memo

    notebook = (ROOT / "NOTEBOOK.md").read_text(encoding="utf-8")
    disclosure = (ROOT / "AI_USAGE.md").read_text(encoding="utf-8")
    assert "Dead end" in notebook or "dead end" in notebook
    assert "Antigravity" in disclosure and "ChatGPT" in disclosure
    assert "Personal verification still required" in disclosure
    print("PASS C/docs: memo labels, notebook, and AI disclosure are present")


def main():
    require_files()
    verify_a1()
    verify_a2()
    verify_a3_a4()
    verify_b()
    verify_c_and_disclosures()
    print("ALL REPOSITORY CHECKS PASSED")
    print("Reminder: this does not replace your own rerun or live defense.")


if __name__ == "__main__":
    main()
