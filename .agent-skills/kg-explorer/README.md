# KG Explorer tools

Utilities for inspecting the final Food-AI claim graph.

## Examples

```bash
python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/vector_search.py \
  "yogurt effect on LDL cholesterol" --top_k 5 --mode lexical

python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/get_claim_details.py \
  407221a36b7d

python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/explore_neighbors.py \
  yogurt food --direction subject

python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/search_entities.py \
  "vitamin D fortified yogurt" --top-k 5

python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/search_by_pmid.py \
  21289226

python .agent-skills/kg-explorer/.claude/skills/kg-explorer/scripts/compare_claims.py \
  407221a36b7d 01e523949fe7
```

## Default data bundle

The tools default to the final paper-facing graph bundle:

- `data/processed/final_graph/food_ai_graph.pkl`
- `data/processed/final_graph/food_ai_graph_networkx.json`
- `data/processed/final_graph/claim_embeddings_bge_m3.json`

Override paths with `FOOD_AI_KG_PICKLE_PATH`, `FOOD_AI_KG_JSON_PATH`, and `FOOD_AI_EMBEDDINGS_PATH` if needed.
