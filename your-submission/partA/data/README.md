# A1 - Multilingual Evaluation Corpus

## Corpus choice and provenance

This audit uses the FLORES-200 `devtest` split. The
[official FLORES-200 documentation](https://github.com/facebookresearch/flores/blob/main/flores200/README.md)
describes a professionally translated benchmark built from 842 web articles
and 3,001 total sentences across its splits. The archive used here was
retrieved on 2026-09-04 from:

`https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz`

The [official repository](https://github.com/facebookresearch/flores) lists
FLORES-200 under CC-BY-SA 4.0.

## Size and languages

The evaluation file contains 1,012 line-aligned sentences in seven languages,
including three Dravidian languages:

| Code | Language | Script | Sentences |
|---|---|---|---:|
| `eng_Latn` | English | Latin | 1,012 |
| `hin_Deva` | Hindi | Devanagari | 1,012 |
| `kan_Knda` | Kannada | Kannada | 1,012 |
| `tam_Taml` | Tamil | Tamil | 1,012 |
| `tel_Telu` | Telugu | Telugu | 1,012 |
| `ben_Beng` | Bengali | Bengali | 1,012 |
| `mar_Deva` | Marathi | Devanagari | 1,012 |

## Reproduction, preprocessing, and integrity

Run:

```bash
python partA/build_corpus.py
```

The builder verifies the archive, extracts only the seven required regular
files, preserves every source line position, requires equal non-empty line
counts, strips outer whitespace only after alignment validation, and writes
LF line endings on every operating system. It does not lowercase, remove
punctuation, transliterate, or normalize Unicode. The corrected analysis later
applies NFC and records that separate policy.

- Audited archive SHA-256:
  `b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6`
- Generated `eval_parallel.jsonl` SHA-256:
  `5dfb45774fae3ad78c7f850995661c41f43dbe4fcc76a215ff6cef6daaa16fdb`
- Machine-readable metadata: `corpus_metadata.json`, including every source
  language-file hash and the output hash.

## What this corpus cannot tell us

FLORES is formal web-article translation data, not a sample of production
assistant traffic. Its 1,012 native-script sentences do not establish costs
for a real mix of short chats, long answers, code-mixing, romanization, typos,
emoji, speech-to-text artifacts, or changing request lengths. One professional
translation per sentence also does not represent every natural way users may
express the same meaning. Therefore this corpus supports a controlled
cross-language tokenizer comparison, but it cannot by itself predict serving
cost, latency, answer quality, or the production traffic-weighted language
mix.
