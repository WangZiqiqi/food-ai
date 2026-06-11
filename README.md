# Food-AI

**Food-AI** is a claim-centric literature graph for mapping fermented food and probiotic health-function evidence.

This repository is the code and reproducibility package for the manuscript:

> *Mapping fermented food and probiotic health-function evidence with a claim-centric literature graph*

The repository contains the core Python package, extraction/evaluation scripts, read-only evidence-query agent code, tests, and the paper-facing graph/evaluation bundle. It intentionally excludes manuscript source files, internal project-management notes, raw logs, local environments, and temporary development artifacts.

## Repository contents

```text
food_ai/      Core extraction, schema, graph-building, embedding, and quality modules
agents/       Agent query/review/refine entry points and SDK runtime helpers
scripts/      Extraction, graph, embedding, and evaluation scripts
tests/        Active regression/smoke tests
config/       Refinement/configuration files
data/         Minimal paper-facing graph and evaluation assets
```

## Paper-facing graph bundle

Current frozen bundle:

```text
data/evaluation/manifests/food_ai_final_manifest.json
```

Main graph artifacts:

```text
data/processed/final_graph/
```

Key graph statistics from the freeze manifest:

| Metric | Value |
| --- | ---: |
| PubMed records | 850 |
| Successful extractions | 850 |
| Extraction errors | 0 |
| Merged claims | 3,786 |
| Evidence items | 4,101 |
| Unique subjects | 621 |
| Unique outcomes | 2,555 |
| Zero-claim articles | 103 |
| Over-specific food entities | 159 |

## Main evaluation assets

- Repaired graph-positive 120-question benchmark:
  `data/evaluation/clean120_benchmark.json`
- Claim-vector retrieval results:
  `data/evaluation/clean120_retrieval_claim_vectors.json`
- Raw abstract vector baseline:
  `data/evaluation/clean120_raw_abstract_baseline.json`
- Full agent QA rescore:
  `data/evaluation/clean120_agent_results.json`
- Independent food-science question set and review summary:
  `data/evaluation/independent_questions_v1.csv`
  `data/evaluation/independent_questions_v1_review_summary.md`
- Compact experiment tables:
  `data/evaluation/experiment_tables.md`

## Environment setup

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync --all-extras
```

Alternatively, with an existing Python environment:

```bash
uv pip install -e ".[dev]"
```

Copy the example environment file if you want to run LLM/embedding/agent calls:

```bash
cp .env.example .env
```

The included graph and evaluation files can be inspected without API keys. Re-running extraction, embedding construction, or agent QA requires provider credentials.

## Quick checks

Run the test suite:

```bash
uv run --extra dev pytest -q
```

Inspect the frozen graph summary:

```bash
python - <<'PY'
import json
p = 'data/evaluation/manifests/food_ai_final_manifest.json'
d = json.load(open(p))
print(json.dumps(d['summaries']['quality'], indent=2))
PY
```

Inspect headline retrieval metrics:

```bash
python - <<'PY'
import json
p = 'data/evaluation/manifests/food_ai_final_manifest.json'
d = json.load(open(p))
print(json.dumps(d['summaries']['clean120_retrieval']['headline'], indent=2))
PY
```

## Notes for reviewers

- The graph is derived from PubMed metadata/abstracts rather than full text.
- Claim-level recall is reported as an index self-consistency check; PMID-level recall is the primary retrieval metric.
- The repository includes the frozen graph/evaluation bundle used for the manuscript tables. Large raw collection caches, development logs, and manuscript source files are excluded.
