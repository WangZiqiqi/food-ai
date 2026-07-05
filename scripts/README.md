# Food-AI scripts

This directory contains the public reproduction scripts for the final Food-AI bundle.

## Core pipeline

- `run_extraction_v3.py` — run the claim-centric extraction pipeline.
- `build_claim_embeddings_v3.py` — build claim embeddings for an extraction file.
- `render_kg_pyvis.py` — render a graph JSON export for interactive inspection.

## Corpus construction

- `fetch_pubmed_data.py` — fetch PubMed metadata.
- `filter_relevance.py` — score article relevance.
- `expand_pubmed_corpus.py` and `select_pubmed_expansion_with_llm.py` — construct the PubMed article pool.

## Evaluation

The `scripts/evaluation/` subdirectory contains benchmark generation, retrieval evaluation, full-agent scoring, raw-abstract baseline, and summary-table utilities for the final graph/evaluation bundle.
