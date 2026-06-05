"""
Extraction prompts — first-line defence layer.
All prompts are in English to ensure consistent English-only output.
"""

# Entity extraction prompt
IMPROVED_ENTITY_PROMPT = """Extract entities from the following biomedical article.

## Strict Extraction Rules

### Strains — highest priority
 Valid examples:
   - "Lactobacillus acidophilus La5"
   - "Bifidobacterium animalis subsp. lactis BB-12"
   - "Lacticaseibacillus paracasei SD1"

 Do NOT extract (too generic to uniquely identify):
   - "LAB", "lactic acid bacteria"
   - "yeast", "bacteria", "probiotics", "microorganisms"
   - "gut microbiota", "intestinal bacteria"
   - Genus-only names: "Lactobacillus", "Bifidobacterium", "Streptococcus"

Requirements:
1. Must include: genus + species + strain designation (e.g. La5, BB-12)
2. If no strain designation is found, try to locate it in the text
3. If only a generic description exists, return []

### Food Products
 Valid examples:
   - "yogurt", "kefir", "kimchi"
   - "fermented_milk", "probiotic_yogurt"

 Do NOT extract:
   - "Fermented food", "dairy product" (too generic)
   - Mixed case: "Yogurt", "YOGURT"

Requirements:
1. All lowercase English
2. Replace spaces with underscores
3. Specific, not generic

### Populations
 Valid examples:
   - "type_2_diabetes", "healthy_adults", "overweight", "prediabetes"

 Do NOT extract:
   - Abbreviations: "T2DM", "diabetics"

Requirements:
1. Use standard medical terminology
2. Lowercase, spaces -> underscores
3. Avoid abbreviations

### Outcomes
 Valid examples:
   - "hba1c", "fasting_glucose", "ldl_cholesterol", "bmi", "body_weight", "crp", "il_6"

 Do NOT extract:
   - Uppercase: "HbA1c", "LDL-C", "BMI"
   - Non-standard: "blood sugar"

Requirements:
1. Use standard abbreviations
2. All lowercase, spaces -> underscores

## Output Format (strictly follow)

```json
{
    "strains": [
        {
            "name": "full strain name",
            "genus": "genus name",
            "species": "species name",
            "strain_id": "strain designation"
        }
    ],
    "food_products": [
        {
            "name": "food name",
            "category": "category"
        }
    ],
    "populations": [
        {
            "name": "population name",
            "condition": "health condition"
        }
    ],
    "outcomes": [
        {
            "name": "outcome name",
            "unit": "unit if applicable"
        }
    ]
}
```

Important:
- Return [] for any entity type not present in the article
- Do not guess — only extract what is explicitly stated
- Return valid JSON only, no explanatory text

Article title: {title}

Article abstract: {abstract}

MeSH terms: {mesh_terms}

Output JSON:
"""


# Claim extraction prompt
IMPROVED_CLAIM_PROMPT = """Extract scientific claims from the following biomedical article.

## Strict Rules

### Effect size format (English only — no other languages)
 Valid:
   - "decreased by 0.76%"
   - "OR 0.292 (95% CI: 0.148–0.577)"
   - "SMD -0.23 [95% CI -0.39 to -0.08]"
   - "mean difference -5.2 mg/dL"

 Invalid (will be flagged as errors):
   - Any non-translated note describing the effect
   - Vague phrases like "significantly decreased" without a numeric value

### Effect direction — use exactly one of:
- "positive"  = beneficial / improves / reduces risk
- "negative"  = harmful / worsens / increases risk
- "neutral"   = no significant effect
- "mixed"     = conflicting results
- "unknown"   = cannot determine

### p-value format
 Valid: "p=0.01", "p<0.05", "p>0.05", "NS"
 Invalid: extra spaces ("p = 0.01"), non-numeric descriptions

### Evidence snippet requirements
Must be a sentence directly from the abstract that supports the claim:
- At least 10 words
- Must contain the key numeric finding

## Output Format

```json
{
    "claims": [
        {
            "subject_type": "strain or food_product",
            "subject_name": "subject name (normalised)",
            "predicate": "has_effect or studied_in",
            "object_type": "outcome or population",
            "object_name": "object name (normalised)",
            "direction": "positive/negative/neutral/mixed/unknown",
            "effect_size": "numeric effect size in English",
            "p_value": "p-value",
            "evidence_snippet": "verbatim supporting sentence (≥10 words)"
        }
    ]
}
```

Important:
- Return [] if no explicit claims can be extracted
- effect_size must be in English
- evidence_snippet must be provided
- Return JSON only, no explanatory text

Title: {title}

Abstract: {abstract}

Identified entities:
- Strains: {strain_names}
- Foods: {food_names}
- Populations: {pop_names}
- Outcomes: {outcome_names}

Output JSON:
"""


# System prompts
ENTITY_SYSTEM_PROMPT = """You are an expert biomedical literature analyst specialising in
fermented foods and probiotics research.

Your task is to accurately extract structured entity information from scientific articles.

Key principles:
1. Precision over recall — when in doubt, do not extract
2. Use standard terminology and formats
3. Be specific — avoid generic terms

Return valid JSON only, no explanatory text."""


CLAIM_SYSTEM_PROMPT = """You are an expert biomedical literature analyst specialising in
fermented foods and probiotics research.

Your task is to accurately extract scientific claims from research articles.

Key principles:
1. Every claim must be directly supported by text in the abstract
2. All effect sizes and descriptions must be in English
3. Provide accurate quantitative data wherever available

Return valid JSON only, no explanatory text."""
