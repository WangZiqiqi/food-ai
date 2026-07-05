---
name: kg-explorer
description: "Knowledge graph exploration tools for the Food-AI V3 claim-centric graph, including claim search, evidence inspection, neighborhood traversal, PMID lookup, and conflict-aware comparison."
---

# KG Explorer

Use this skill to explore the Food-AI claim-centric knowledge graph in read-only mode.

## Core graph model

Food-AI V3 uses a claim-centric representation:

- A **claim** is the primary evidence unit after canonicalization and deduplication.
- Evidence is stored inside each claim as `evidence_list`.
- A single claim may aggregate multiple PubMed sources.
- Entities such as foods, strains, outcomes, and populations are graph nodes connected to claim nodes.

### Claim fields

Each claim typically contains:

```json
{
  "claim_id": "12-character hash",
  "claim_text": "yogurt has positive effect on type_2_diabetes",
  "subject_name": "yogurt",
  "subject_type": "food",
  "object_name": "type_2_diabetes",
  "object_type": "outcome",
  "direction": "positive|negative|neutral|mixed",
  "confidence_score": 0.85,
  "evidence_count": 2,
  "evidence_list": [
    {
      "pmid": "...",
      "study_type": "RCT|review|meta_analysis|...",
      "effect_size": "...",
      "p_value": "...",
      "evidence_snippet": "..."
    }
  ]
}
```

## Exploration strategy

Recommended workflow:

1. Start with `vector_search.py` to retrieve candidate claims for the question.
2. Inspect high-priority candidates with `get_claim_details.py`.
3. Traverse local graph neighborhoods with `explore_neighbors.py`.
4. Use `search_entities.py` to confirm canonical entity names.
5. Use `search_by_pmid.py` when validating which claims came from a specific PubMed paper.
6. Use `compare_claims.py` to check whether multiple claims share subjects, outcomes, evidence, or conflicting directions.

## Tool reference

### `vector_search.py`

Semantic or lexical claim retrieval.

```bash
python vector_search.py "yogurt effect on diabetes" --top_k 5
python vector_search.py "yogurt effect on diabetes" --top_k 5 --mode lexical
```

Returns claim IDs, claim texts, and similarity scores.

### `get_claim_details.py`

Inspect a single claim in detail.

```bash
python get_claim_details.py <claim_id>
```

Returns subject, object, direction, confidence, evidence list, PMIDs, study types, and snippets.

### `explore_neighbors.py`

Traverse the graph around an entity.

```bash
python explore_neighbors.py yogurt food --direction subject
python explore_neighbors.py type_2_diabetes outcome --direction object
```

Directions:

- `subject`: claims where the entity is the subject.
- `object`: claims where the entity is the object.
- `both`: both directions.

### `search_entities.py`

Find entity nodes by name.

```bash
python search_entities.py yogurt --top-k 5
```

### `search_by_pmid.py`

Find graph claims supported by a PubMed article.

```bash
python search_by_pmid.py 21289226
```

### `compare_claims.py`

Compare two or more claims.

```bash
python compare_claims.py <claim_id_1> <claim_id_2>
```

## Interpretation guidance

- Prefer claims with more evidence and stronger study designs.
- Always report PMID traceability for evidence-backed answers.
- Treat conflicting directions as evidence heterogeneity, not necessarily graph error.
- If the graph does not contain relevant evidence, answer with an explicit graph-relative abstention.
