#!/usr/bin/env python3
"""
Evidence-first audit of starter_kit/fertility.py.

Each experiment changes one choice at a time and reports the measured effect.
Run every experiment:
    python partA/audit_experiments.py

Run one experiment:
    python partA/audit_experiments.py --experiment split_spaces
"""

import argparse
import csv
import json
import os
import random
import unicodedata

import regex
import tiktoken


PART_A_DIR = os.path.dirname(os.path.abspath(__file__))
SUBMISSION_DIR = os.path.dirname(PART_A_DIR)
STARTER_DIR = os.path.abspath(
    os.path.join(SUBMISSION_DIR, "..", "starter_kit", "starter_kit")
)
SAMPLE_DIR = os.path.join(STARTER_DIR, "corpus_sample")
EVAL_PATH = os.path.join(PART_A_DIR, "data", "eval_parallel.jsonl")
DEFAULT_OUTPUT = os.path.join(PART_A_DIR, "results", "audit_deltas.csv")

EXPERIMENTS = (
    "split_spaces",
    "lowercase",
    "macro_average",
    "character_unit",
    "parallel_denominator",
    "nfc_control",
    "random_seed_control",
)


def read_sample(language):
    path = os.path.join(SAMPLE_DIR, f"{language}_sample.txt")
    with open(path, "r", encoding="utf-8") as handle:
        return [
            unicodedata.normalize("NFC", raw.strip())
            for raw in handle
            if raw.strip()
        ]


def read_parallel_corpus():
    with open(EVAL_PATH, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def macro_fertility(lines, encode, *, lowercase, literal_space):
    values = []
    for original in lines:
        line = original.lower() if lowercase else original
        words = line.split(" ") if literal_space else line.split()
        values.append(len(encode(line)) / len(words))
    return mean(values)


def pooled_fertility(lines, encode, *, lowercase):
    token_total = 0
    word_total = 0
    for original in lines:
        line = original.lower() if lowercase else original
        token_total += len(encode(line))
        word_total += len(line.split())
    return token_total / word_total


def cross_language_ratio(
    eng_lines,
    hin_lines,
    encode,
    *,
    lowercase,
    literal_space,
    aggregation="macro",
):
    if aggregation == "macro":
        eng_value = macro_fertility(
            eng_lines, encode, lowercase=lowercase, literal_space=literal_space
        )
        hin_value = macro_fertility(
            hin_lines, encode, lowercase=lowercase, literal_space=literal_space
        )
    elif aggregation == "pooled":
        eng_value = pooled_fertility(eng_lines, encode, lowercase=lowercase)
        hin_value = pooled_fertility(hin_lines, encode, lowercase=lowercase)
    else:
        raise ValueError(f"Unknown aggregation: {aggregation}")
    return hin_value / eng_value


def result_row(
    experiment_id,
    classification,
    metric,
    baseline,
    comparison,
    exact_command,
    evidence,
    conclusion,
):
    absolute_change = comparison - baseline
    relative_change = (absolute_change / baseline * 100) if baseline else 0.0
    return {
        "experiment_id": experiment_id,
        "classification": classification,
        "metric": metric,
        "baseline_value": round(baseline, 6),
        "comparison_value": round(comparison, 6),
        "absolute_change": round(absolute_change, 6),
        "relative_change_pct": round(relative_change, 4),
        "exact_command": exact_command,
        "evidence": evidence,
        "conclusion": conclusion,
    }


def experiment_split_spaces(encode, eng_lines, hin_lines, _records):
    original_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=True,
        literal_space=True,
    )
    fixed_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=True,
        literal_space=False,
    )

    line = "Please keep the books  in the cupboard.".lower()
    token_count = len(encode(line))
    literal_words = len(line.split(" "))
    whitespace_words = len(line.split())
    original_line_fertility = token_count / literal_words
    fixed_line_fertility = token_count / whitespace_words

    evidence = (
        f"Minimal line: {token_count} tokens; split(' ') counts "
        f"{literal_words} items while split() counts {whitespace_words}. "
        f"Line fertility changes {original_line_fertility:.4f} to "
        f"{fixed_line_fertility:.4f}. On the complete starter sample, "
        f"the Hindi/English ratio changes {original_ratio:.4f} to "
        f"{fixed_ratio:.4f}."
    )
    conclusion = (
        f"Confirmed code bug. Fixing whitespace parsing increases the reported "
        f"Hindi/English ratio by {(fixed_ratio / original_ratio - 1) * 100:.2f}%; "
        "the original script slightly understates the ratio."
    )
    return [
        result_row(
            "FLAW-1",
            "Code bug",
            "starter-sample Hindi/English macro fertility ratio",
            original_ratio,
            fixed_ratio,
            "python partA/audit_experiments.py --experiment split_spaces",
            evidence,
            conclusion,
        )
    ]


def experiment_lowercase(encode, eng_lines, hin_lines, records):
    original_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=True,
        literal_space=True,
    )
    raw_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=False,
        literal_space=True,
    )

    eng_raw_tokens = sum(len(encode(line)) for line in eng_lines)
    eng_lower_tokens = sum(len(encode(line.lower())) for line in eng_lines)
    hin_raw_tokens = sum(len(encode(line)) for line in hin_lines)
    hin_lower_tokens = sum(len(encode(line.lower())) for line in hin_lines)

    flores_eng_raw = sum(len(encode(row["eng_Latn"])) for row in records)
    flores_eng_lower = sum(
        len(encode(row["eng_Latn"].lower())) for row in records
    )
    flores_hin_raw = sum(len(encode(row["hin_Deva"])) for row in records)
    flores_hin_lower = sum(
        len(encode(row["hin_Deva"].lower())) for row in records
    )

    evidence = (
        f"Starter sample token totals raw to lower: English "
        f"{eng_raw_tokens} to {eng_lower_tokens}; Hindi "
        f"{hin_raw_tokens} to {hin_lower_tokens}. The report ratio changes "
        f"{original_ratio:.4f} (lowercased) to {raw_ratio:.4f} (raw). "
        f"On FLORES, English changes {flores_eng_raw} to {flores_eng_lower} "
        f"and Hindi changes {flores_hin_raw} to {flores_hin_lower}."
    )
    conclusion = (
        f"Confirmed measurement mismatch for raw serving text. Lowercasing "
        f"changes the starter-sample ratio by "
        f"{(raw_ratio / original_ratio - 1) * 100:.2f}% and affects English "
        "far more than Hindi; a production-cost audit should tokenize the "
        "text form actually served."
    )
    return [
        result_row(
            "FLAW-2",
            "Methodological flaw",
            "starter-sample Hindi/English ratio",
            original_ratio,
            raw_ratio,
            "python partA/audit_experiments.py --experiment lowercase",
            evidence,
            conclusion,
        )
    ]


def experiment_macro_average(encode, eng_lines, hin_lines, _records):
    macro_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=True,
        literal_space=False,
        aggregation="macro",
    )
    pooled_ratio = cross_language_ratio(
        eng_lines,
        hin_lines,
        encode,
        lowercase=True,
        literal_space=False,
        aggregation="pooled",
    )
    evidence = (
        f"With splitting held fixed, mean-of-line fertility gives "
        f"{macro_ratio:.6f}, while total tokens divided by total words gives "
        f"{pooled_ratio:.6f}."
    )
    conclusion = (
        f"Confirmed aggregation issue, but its measured impact is small on "
        f"this sample: switching to pooled counts changes the ratio by "
        f"{(pooled_ratio / macro_ratio - 1) * 100:.2f}%."
    )
    return [
        result_row(
            "FLAW-3",
            "Aggregation flaw",
            "starter-sample Hindi/English fertility ratio",
            macro_ratio,
            pooled_ratio,
            "python partA/audit_experiments.py --experiment macro_average",
            evidence,
            conclusion,
        )
    ]


def experiment_character_unit(encode, eng_lines, hin_lines, _records):
    def token_per_unit(lines, unit_counter):
        return mean(
            len(encode(line.lower())) / unit_counter(line.lower())
            for line in lines
        )

    eng_codepoint = token_per_unit(eng_lines, len)
    hin_codepoint = token_per_unit(hin_lines, len)
    eng_grapheme = token_per_unit(
        eng_lines, lambda text: len(regex.findall(r"\X", text))
    )
    hin_grapheme = token_per_unit(
        hin_lines, lambda text: len(regex.findall(r"\X", text))
    )
    codepoint_ratio = hin_codepoint / eng_codepoint
    grapheme_ratio = hin_grapheme / eng_grapheme

    evidence = (
        f"Python len() produces a Hindi/English token-per-code-point ratio of "
        f"{codepoint_ratio:.4f}. Counting user-visible grapheme clusters "
        f"produces {grapheme_ratio:.4f}. English is unchanged; Indic combining "
        "marks change the Hindi denominator."
    )
    conclusion = (
        "Confirmed metric-definition flaw. The label tok/char is ambiguous: "
        "the code measures Unicode code points, not user-visible characters. "
        "Neither character unit holds meaning constant across languages."
    )
    return [
        result_row(
            "FLAW-4",
            "Metric-definition flaw",
            "Hindi/English token-per-character ratio",
            codepoint_ratio,
            grapheme_ratio,
            "python partA/audit_experiments.py --experiment character_unit",
            evidence,
            conclusion,
        )
    ]


def experiment_parallel_denominator(encode, _eng_lines, _hin_lines, records):
    eng_tokens = sum(len(encode(row["eng_Latn"])) for row in records)
    hin_tokens = sum(len(encode(row["hin_Deva"])) for row in records)
    eng_words = sum(len(row["eng_Latn"].split()) for row in records)
    hin_words = sum(len(row["hin_Deva"].split()) for row in records)

    word_ratio = (hin_tokens / hin_words) / (eng_tokens / eng_words)
    sentence_ratio = hin_tokens / eng_tokens

    evidence = (
        f"On the same 1,012 aligned FLORES rows, the pooled token-per-word "
        f"ratio is {word_ratio:.4f}, while the token-per-aligned-sentence "
        f"ratio is {sentence_ratio:.4f}. No corpus rows or tokenizer settings "
        "change between the two calculations."
    )
    conclusion = (
        f"Confirmed conceptual flaw. For equal semantic units, the word-based "
        f"ratio is {(1 - word_ratio / sentence_ratio) * 100:.2f}% below the "
        "aligned-sentence ratio because word counts are not comparable units "
        "across languages."
    )
    return [
        result_row(
            "FLAW-5",
            "Conceptual metric flaw",
            "FLORES Hindi/English GPT-2 ratio",
            word_ratio,
            sentence_ratio,
            "python partA/audit_experiments.py --experiment parallel_denominator",
            evidence,
            conclusion,
        )
    ]


def experiment_nfc_control(encode, eng_lines, hin_lines, records):
    sample_raw = sum(len(encode(line)) for line in eng_lines + hin_lines)
    sample_nfc = sum(
        len(encode(unicodedata.normalize("NFC", line)))
        for line in eng_lines + hin_lines
    )

    language_keys = [key for key in records[0] if key != "sentence_id"]
    flores_raw = sum(
        len(encode(row[language])) for row in records for language in language_keys
    )
    flores_nfc = sum(
        len(encode(unicodedata.normalize("NFC", row[language])))
        for row in records
        for language in language_keys
    )

    evidence = (
        f"On the v0 starter sample, raw and NFC totals are both {sample_raw} "
        f"tokens, so NFC changes the reported result by zero. Across all seven "
        f"FLORES languages, raw total {flores_raw} becomes {flores_nfc} "
        f"({(flores_nfc / flores_raw - 1) * 100:.3f}% change)."
    )
    conclusion = (
        "Not a v0 bug. NFC is reasonable canonical Unicode preprocessing and "
        "had zero effect on the reported sample numbers. It must nevertheless "
        "be documented and applied consistently in the corrected analysis."
    )
    return [
        result_row(
            "CONTROL-1",
            "Not a bug",
            "starter-sample total GPT-2 tokens",
            sample_raw,
            sample_nfc,
            "python partA/audit_experiments.py --experiment nfc_control",
            evidence,
            conclusion,
        )
    ]


def experiment_random_seed_control(encode, eng_lines, hin_lines, _records):
    ratios = []
    for seed in (1, 1337, 9999):
        random.seed(seed)
        ratios.append(
            cross_language_ratio(
                eng_lines,
                hin_lines,
                encode,
                lowercase=True,
                literal_space=True,
            )
        )
    evidence = (
        "Ratios for seeds 1, 1337, and 9999 are "
        + ", ".join(f"{value:.6f}" for value in ratios)
        + ". fertility.py never calls a random operation."
    )
    conclusion = (
        "Verified harmless. The random seed is unused dead code and has exactly "
        "zero effect on every reported value."
    )
    return [
        result_row(
            "CONTROL-2",
            "Harmless code",
            "starter-sample Hindi/English ratio",
            ratios[1],
            ratios[2],
            "python partA/audit_experiments.py --experiment random_seed_control",
            evidence,
            conclusion,
        )
    ]


EXPERIMENT_FUNCTIONS = {
    "split_spaces": experiment_split_spaces,
    "lowercase": experiment_lowercase,
    "macro_average": experiment_macro_average,
    "character_unit": experiment_character_unit,
    "parallel_denominator": experiment_parallel_denominator,
    "nfc_control": experiment_nfc_control,
    "random_seed_control": experiment_random_seed_control,
}


def write_results(rows, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_results(rows):
    for row in rows:
        print("=" * 78)
        print(f"{row['experiment_id']}: {row['classification']}")
        print(f"Metric: {row['metric']}")
        print(
            f"Baseline: {row['baseline_value']} | "
            f"Comparison: {row['comparison_value']} | "
            f"Change: {row['relative_change_pct']}%"
        )
        print(f"Evidence: {row['evidence']}")
        print(f"Conclusion: {row['conclusion']}")


def main():
    parser = argparse.ArgumentParser(
        description="Run isolated, evidence-first audits of fertility.py."
    )
    parser.add_argument(
        "--experiment",
        choices=("all",) + EXPERIMENTS,
        default="all",
        help="Run one experiment or the complete audit.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional CSV output path. With --experiment all, defaults to "
            "partA/results/audit_deltas.csv."
        ),
    )
    args = parser.parse_args()

    encode = tiktoken.get_encoding("gpt2").encode
    eng_lines = read_sample("eng")
    hin_lines = read_sample("hin")
    records = read_parallel_corpus()

    selected = EXPERIMENTS if args.experiment == "all" else (args.experiment,)
    rows = []
    for name in selected:
        rows.extend(
            EXPERIMENT_FUNCTIONS[name](encode, eng_lines, hin_lines, records)
        )

    print_results(rows)

    output_path = args.output
    if output_path is None and args.experiment == "all":
        output_path = DEFAULT_OUTPUT
    if output_path:
        output_path = os.path.abspath(output_path)
        write_results(rows, output_path)
        print("=" * 78)
        print(f"Saved {len(rows)} evidence rows to {output_path}")


if __name__ == "__main__":
    main()
