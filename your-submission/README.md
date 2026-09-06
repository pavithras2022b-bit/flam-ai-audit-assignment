# AI Team Intern Assignment - Audited Submission Candidate

This working copy preserves the Antigravity-generated first draft and rebuilds
it one section at a time. **All take-home sections, A1 through C, have completed
evidence-level revision.** The repository still requires the student's own
local rerun and mock-defense practice before it should be submitted.

## Structure

- `partA/`: Hash-verified corpus builder and metadata, corrected A2 isolating
  experiments, reproducible multi-denominator analysis, and the revised
  one-page recommendation memo.
- `partB/`: Corrected serving-capacity arithmetic, generated-output goodput
  derivation, anomaly diagnosis, a reproducible results table, and a hashed
  verification summary.
- `partC/`: Revised one-page decision memo with labelled assumptions,
  arithmetic, launch gate, kill criterion, and Day-1 experiment.
- `NOTEBOOK.md`: Honest chronological record beginning with the audit of the
  AI-generated draft.
- `AI_USAGE.md`: Current disclosure of Antigravity and ChatGPT assistance,
  including personal-verification steps still outstanding.
- `DEFENSE_GUIDE.md`: Plain-language explanations, counterfactuals, practice
  commands, and the student's final checklist.
- `run_all.py`: Master runner to reproduce all pipeline data and tables from scratch.
- `verify_submission.py`: Fail-fast checks for files, hashes, row counts,
  arithmetic outputs, required memo labels, and disclosure documents.

## Setup & Running

```bash
pip install -r requirements.txt
python run_all.py
python verify_submission.py
```

The verified FLORES archive is included, so the default corpus rebuild does not
need a new download.

To verify Part B alone:

```bash
python partB/analyze_bench.py
```
