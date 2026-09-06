#!/usr/bin/env python3
"""Build the aligned seven-language FLORES-200 evaluation corpus.

The builder verifies the exact archive used for the audit, preserves source
line positions, rejects incomplete rows instead of silently shifting alignment,
and writes machine-readable provenance metadata.
"""

import argparse
import hashlib
import json
import os
import tarfile
import urllib.request
from pathlib import Path


FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
EXPECTED_ARCHIVE_SHA256 = (
    "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6"
)
SPLIT = "devtest"
LANGUAGES = (
    "eng_Latn",
    "hin_Deva",
    "kan_Knda",
    "tam_Taml",
    "tel_Telu",
    "ben_Beng",
    "mar_Deva",
)

PART_A_DIR = Path(__file__).resolve().parent
DATA_DIR = PART_A_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DEFAULT_ARCHIVE = RAW_DIR / "flores200_dataset.tar.gz"
DEFAULT_OUTPUT = DATA_DIR / "eval_parallel.jsonl"
DEFAULT_METADATA = DATA_DIR / "corpus_metadata.json"


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_archive(archive_path):
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        print(f"Downloading FLORES-200 from {FLORES_URL}")
        urllib.request.urlretrieve(FLORES_URL, archive_path)

    actual_hash = file_sha256(archive_path)
    if actual_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(
            "FLORES archive hash mismatch: "
            f"expected {EXPECTED_ARCHIVE_SHA256}, got {actual_hash}"
        )
    print(f"Verified archive SHA-256: {actual_hash}")
    return actual_hash


def extract_required_files(archive_path):
    """Extract only the required regular files to explicit safe paths."""
    destination = RAW_DIR / "flores200_dataset" / SPLIT
    destination.mkdir(parents=True, exist_ok=True)
    extracted = {}

    with tarfile.open(archive_path, "r:gz") as archive:
        members = {
            member.name.lstrip("./"): member
            for member in archive.getmembers()
            if member.isfile()
        }
        for language in LANGUAGES:
            member_name = f"flores200_dataset/{SPLIT}/{language}.{SPLIT}"
            member = members.get(member_name)
            if member is None:
                raise FileNotFoundError(
                    f"Archive is missing required member {member_name}"
                )
            source = archive.extractfile(member)
            if source is None:
                raise OSError(f"Could not read archive member {member_name}")
            output_path = destination / f"{language}.{SPLIT}"
            with source, open(output_path, "wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            extracted[language] = output_path

    return extracted


def load_aligned_lines(extracted_files):
    language_lines = {}
    for language in LANGUAGES:
        path = extracted_files[language]
        # splitlines removes line terminators but preserves empty line positions.
        lines = path.read_text(encoding="utf-8").splitlines()
        language_lines[language] = lines

    line_counts = {language: len(lines) for language, lines in language_lines.items()}
    if len(set(line_counts.values())) != 1:
        raise ValueError(f"Language files have different line counts: {line_counts}")

    sentence_count = next(iter(line_counts.values()), 0)
    if sentence_count == 0:
        raise ValueError("FLORES split is empty")

    for index in range(sentence_count):
        empty_languages = [
            language
            for language in LANGUAGES
            if not language_lines[language][index].strip()
        ]
        if empty_languages:
            raise ValueError(
                f"Empty aligned text at source line {index + 1}: "
                f"{empty_languages}"
            )
    return language_lines, sentence_count


def write_parallel_corpus(language_lines, sentence_count, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        for index in range(sentence_count):
            record = {"sentence_id": index + 1}
            for language in LANGUAGES:
                # Strip only after shared line positions have been validated.
                # This retains the original audit corpus while avoiding the
                # alignment shift caused by independently filtering blanks.
                record[language] = language_lines[language][index].strip()
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return file_sha256(output_path)


def write_metadata(
    metadata_path,
    archive_path,
    archive_hash,
    extracted_files,
    output_path,
    output_hash,
    sentence_count,
):
    metadata = {
        "source_dataset": "FLORES-200",
        "source_url": FLORES_URL,
        "split": SPLIT,
        "archive_path": os.path.relpath(archive_path, PART_A_DIR.parent),
        "archive_sha256": archive_hash,
        "output_path": os.path.relpath(output_path, PART_A_DIR.parent),
        "output_sha256": output_hash,
        "parallel_sentences": sentence_count,
        "languages": list(LANGUAGES),
        "language_files": {
            language: {
                "lines": sentence_count,
                "sha256": file_sha256(extracted_files[language]),
            }
            for language in LANGUAGES
        },
        "build_preprocessing": {
            "line_terminators": "removed by str.splitlines()",
            "blank_lines": "preserved during loading; any blank aligned row fails",
            "outer_whitespace": "stripped only after alignment validation",
            "text_content": "no case, punctuation, or Unicode normalization",
            "alignment": "source line index shared across every language",
        },
    }
    metadata_path = Path(metadata_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Build the verified seven-language FLORES-200 corpus."
    )
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--metadata-output", default=str(DEFAULT_METADATA))
    args = parser.parse_args()

    archive_path = Path(args.archive).resolve()
    output_path = Path(args.output).resolve()
    metadata_path = Path(args.metadata_output).resolve()

    archive_hash = ensure_archive(archive_path)
    extracted_files = extract_required_files(archive_path)
    language_lines, sentence_count = load_aligned_lines(extracted_files)
    output_hash = write_parallel_corpus(
        language_lines, sentence_count, output_path
    )
    write_metadata(
        metadata_path,
        archive_path,
        archive_hash,
        extracted_files,
        output_path,
        output_hash,
        sentence_count,
    )

    print(
        f"Saved {sentence_count} aligned sentences in {len(LANGUAGES)} "
        f"languages to {output_path}"
    )
    print(f"Corpus SHA-256: {output_hash}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
