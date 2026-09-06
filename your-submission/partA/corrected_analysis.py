#!/usr/bin/env python3
r"""
Corrected cross-language tokenizer analysis on aligned FLORES-200 sentences.

The headline measure is mean tokens per aligned sentence and its ratio to
English. Word, grapheme-cluster, and UTF-8-byte measures are reported as
secondary diagnostics. All corpus-level rates use pooled totals.
"""

import argparse
import csv
import hashlib
import json
import os
import unicodedata
from importlib.metadata import version

import numpy as np
import regex
import tiktoken
from transformers import AutoTokenizer


PART_A_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(PART_A_DIR, "data", "eval_parallel.jsonl")
DEFAULT_OUTPUT = os.path.join(PART_A_DIR, "results", "corrected_metrics.csv")
DEFAULT_METADATA = os.path.join(PART_A_DIR, "results", "analysis_metadata.json")

LANGUAGES = (
    ("eng_Latn", "English"),
    ("hin_Deva", "Hindi"),
    ("kan_Knda", "Kannada"),
    ("tam_Taml", "Tamil"),
    ("tel_Telu", "Telugu"),
    ("ben_Beng", "Bengali"),
    ("mar_Deva", "Marathi"),
)

TOKENIZER_SPECS = {
    "gpt2": {
        "name": "GPT-2 (tiktoken)",
        "source": "gpt2",
        "kind": "tiktoken",
        "revision": "tiktoken-0.14.0",
        "role": "English-centric decoder-tokenizer baseline",
    },
    "indicbert": {
        "name": "IndicBERTv2 tokenizer",
        "source": "ai4bharat/IndicBERTv2-MLM-only",
        "kind": "huggingface",
        "revision": "8598f13fe52443bc3fc054fcd665944560145b5c",
        "role": "Indic-aware reference tokenizer; not a drop-in decoder model",
    },
    "qwen2.5": {
        "name": "Qwen2.5-0.5B tokenizer",
        "source": "Qwen/Qwen2.5-0.5B",
        "kind": "huggingface",
        "revision": "060db6499f32faf8b98477b0a26969ef7d8b9987",
        "role": "Tokenizer from a decoder-only generative model family",
    },
}


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preprocess(text):
    return unicodedata.normalize("NFC", text.strip())


def load_corpus(path):
    records = []
    expected_keys = {code for code, _name in LANGUAGES}
    seen_ids = set()

    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            sentence_id = row.get("sentence_id")
            if sentence_id in seen_ids:
                raise ValueError(f"Duplicate sentence_id {sentence_id}")
            seen_ids.add(sentence_id)

            missing = expected_keys - set(row)
            if missing:
                raise ValueError(
                    f"Line {line_number} is missing languages: {sorted(missing)}"
                )

            cleaned = {"sentence_id": sentence_id}
            for language in expected_keys:
                text = preprocess(row[language])
                if not text:
                    raise ValueError(
                        f"Empty {language} text at sentence_id {sentence_id}"
                    )
                cleaned[language] = text
            records.append(cleaned)

    if not records:
        raise ValueError("Evaluation corpus is empty")
    return records


def load_encoder(spec):
    if spec["kind"] == "tiktoken":
        encoding = tiktoken.get_encoding(spec["source"])
        return encoding.encode

    tokenizer = AutoTokenizer.from_pretrained(
        spec["source"],
        revision=spec["revision"],
        trust_remote_code=False,
    )
    return lambda text: tokenizer.encode(text, add_special_tokens=False)


def paired_bootstrap_ratio(language_tokens, english_tokens, samples, seed):
    language_tokens = np.asarray(language_tokens, dtype=np.float64)
    english_tokens = np.asarray(english_tokens, dtype=np.float64)
    if language_tokens.shape != english_tokens.shape:
        raise ValueError("Paired bootstrap arrays must have equal length")

    rng = np.random.default_rng(seed)
    ratios = np.empty(samples, dtype=np.float64)
    n = language_tokens.size
    for index in range(samples):
        selected = rng.integers(0, n, size=n)
        ratios[index] = (
            language_tokens[selected].sum() / english_tokens[selected].sum()
        )
    return (
        float(np.percentile(ratios, 2.5)),
        float(np.percentile(ratios, 97.5)),
    )


def collect_language_counts(records, encode):
    counts = {}
    for language, _name in LANGUAGES:
        sentence_tokens = []
        total_words = 0
        total_graphemes = 0
        total_bytes = 0

        for row in records:
            text = row[language]
            sentence_tokens.append(len(encode(text)))
            total_words += len(text.split())
            total_graphemes += len(regex.findall(r"\X", text))
            total_bytes += len(text.encode("utf-8"))

        counts[language] = {
            "sentence_tokens": np.asarray(sentence_tokens, dtype=np.int64),
            "total_words": total_words,
            "total_graphemes": total_graphemes,
            "total_bytes": total_bytes,
        }
    return counts


def analyse_tokenizer(key, spec, records, bootstrap_samples, seed):
    encode = load_encoder(spec)
    counts = collect_language_counts(records, encode)
    english = counts["eng_Latn"]
    english_total_tokens = int(english["sentence_tokens"].sum())
    english_rates = {
        "word": english_total_tokens / english["total_words"],
        "grapheme": english_total_tokens / english["total_graphemes"],
        "byte": english_total_tokens / english["total_bytes"],
    }

    results = []
    for language_index, (language, language_name) in enumerate(LANGUAGES):
        data = counts[language]
        tokens = data["sentence_tokens"]
        total_tokens = int(tokens.sum())
        token_per_word = total_tokens / data["total_words"]
        token_per_grapheme = total_tokens / data["total_graphemes"]
        token_per_byte = total_tokens / data["total_bytes"]
        sentence_ratio = total_tokens / english_total_tokens
        ci_low, ci_high = paired_bootstrap_ratio(
            tokens,
            english["sentence_tokens"],
            samples=bootstrap_samples,
            seed=seed + language_index,
        )

        results.append(
            {
                "tokenizer_key": key,
                "tokenizer_name": spec["name"],
                "tokenizer_source": spec["source"],
                "tokenizer_revision": spec["revision"],
                "tokenizer_role": spec["role"],
                "language_code": language,
                "language": language_name,
                "sentences": len(records),
                "total_tokens": total_tokens,
                "mean_tokens_per_sentence": round(float(tokens.mean()), 4),
                "median_tokens_per_sentence": round(float(np.median(tokens)), 4),
                "std_tokens_per_sentence": round(float(tokens.std()), 4),
                "sentence_ratio_to_english": round(sentence_ratio, 4),
                "sentence_ratio_ci95_low": round(ci_low, 4),
                "sentence_ratio_ci95_high": round(ci_high, 4),
                "pooled_tokens_per_word": round(token_per_word, 4),
                "word_ratio_to_english": round(
                    token_per_word / english_rates["word"], 4
                ),
                "pooled_tokens_per_grapheme": round(token_per_grapheme, 4),
                "grapheme_ratio_to_english": round(
                    token_per_grapheme / english_rates["grapheme"], 4
                ),
                "pooled_tokens_per_utf8_byte": round(token_per_byte, 4),
                "byte_ratio_to_english": round(
                    token_per_byte / english_rates["byte"], 4
                ),
            }
        )
    return results


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(path, corpus_path, records, selected_keys, samples, seed):
    metadata = {
        "corpus_path": os.path.relpath(corpus_path, os.path.dirname(PART_A_DIR)),
        "corpus_sha256": file_sha256(corpus_path),
        "parallel_sentences": len(records),
        "languages": [code for code, _name in LANGUAGES],
        "preprocessing": {
            "unicode_normalization": "NFC",
            "case": "preserved",
            "punctuation": "preserved",
            "outer_whitespace": "stripped",
        },
        "headline_metric": (
            "ratio of total tokens across aligned sentences to English total"
        ),
        "secondary_metrics": (
            "pooled tokens per whitespace word, grapheme cluster, and UTF-8 byte"
        ),
        "bootstrap": {
            "method": "paired sentence resampling, percentile 95% interval",
            "samples": samples,
            "seed": seed,
        },
        "tokenizers": {
            key: TOKENIZER_SPECS[key] for key in selected_keys
        },
        "package_versions": {
            package: version(package)
            for package in (
                "numpy",
                "regex",
                "tiktoken",
                "tokenizers",
                "transformers",
            )
        },
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def print_summary(rows):
    print(
        f"{'Tokenizer':<29}{'Language':<11}{'Tok/sent':>10}"
        f"{'Ratio':>9}{'95% CI':>18}{'Tok/word':>11}"
    )
    print("-" * 88)
    for row in rows:
        interval = (
            f"[{row['sentence_ratio_ci95_low']:.2f}, "
            f"{row['sentence_ratio_ci95_high']:.2f}]"
        )
        print(
            f"{row['tokenizer_name']:<29}{row['language']:<11}"
            f"{row['mean_tokens_per_sentence']:>10.2f}"
            f"{row['sentence_ratio_to_english']:>9.2f}"
            f"{interval:>18}"
            f"{row['pooled_tokens_per_word']:>11.2f}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run the corrected multilingual tokenizer analysis."
    )
    parser.add_argument(
        "--tokenizer",
        choices=("all",) + tuple(TOKENIZER_SPECS),
        default="all",
        help="Evaluate every tokenizer or one tokenizer in isolation.",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=1000,
        help="Number of paired bootstrap resamples.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        help=(
            "Optional CSV path. A full run defaults to "
            "partA/results/corrected_metrics.csv; a one-tokenizer run prints "
            "only unless a path is supplied."
        ),
    )
    parser.add_argument("--metadata-output")
    args = parser.parse_args()

    if args.bootstrap_samples < 1:
        parser.error("--bootstrap-samples must be at least 1")

    records = load_corpus(CORPUS_PATH)
    selected_keys = (
        tuple(TOKENIZER_SPECS)
        if args.tokenizer == "all"
        else (args.tokenizer,)
    )

    rows = []
    for key in selected_keys:
        rows.extend(
            analyse_tokenizer(
                key,
                TOKENIZER_SPECS[key],
                records,
                bootstrap_samples=args.bootstrap_samples,
                seed=args.seed,
            )
        )

    print_summary(rows)

    output_path = args.output
    metadata_path = args.metadata_output
    if args.tokenizer == "all":
        output_path = output_path or DEFAULT_OUTPUT
        metadata_path = metadata_path or DEFAULT_METADATA

    if output_path:
        output_path = os.path.abspath(output_path)
        write_csv(rows, output_path)
        print(f"\nSaved {len(rows)} result rows to {output_path}")
    if metadata_path:
        metadata_path = os.path.abspath(metadata_path)
        write_metadata(
            metadata_path,
            CORPUS_PATH,
            records,
            selected_keys,
            args.bootstrap_samples,
            args.seed,
        )
        print(f"Saved analysis metadata to {metadata_path}")


if __name__ == "__main__":
    main()
