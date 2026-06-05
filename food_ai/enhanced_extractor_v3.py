"""
Food-AI translated note V3 - Claim-Centric translated note
translated note:
1. Claim translated note(evidence_list)
2. translated note(translated note + LLM translated note)
3. Dose translated note
4. translated note Institution translated note
"""

import json
import re
import hashlib
import pickle
import os
import math
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

import networkx as nx

# translated note
try:
    from llm_client import get_llm_client
    from entity_validator import EntityValidator, StrainValidator, FoodNameNormalizer
    from embedding_client import get_embedding_client
    from build_quality import summarize_extraction_quality
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from llm_client import get_llm_client
    from entity_validator import EntityValidator, StrainValidator, FoodNameNormalizer
    from embedding_client import get_embedding_client
    from build_quality import summarize_extraction_quality


@dataclass
class ExtractedClaim:
    """translated note Claim"""
    subject_type: str
    subject_name: str
    object_type: str
    object_name: str
    direction: str
    effect_direction: str = "unclear"
    health_interpretation: str = "unclear"
    effect_size: Optional[str] = None
    p_value: Optional[str] = None
    evidence_snippet: str = ""
    dose_info: Optional[Dict] = None
    pmid: str = ""
    study_type: str = ""
    confidence: str = "medium"

    def to_claim_text(self) -> str:
        """translated note claim translated note"""
        return (
            f"{self.subject_name} has {self.direction} effect on {self.object_name} "
            f"(measured effect: {self.effect_direction}; "
            f"health interpretation: {self.health_interpretation})"
        )

    def generate_claim_id(self) -> str:
        """translated note claim ID"""
        # translated note
        key = f"{self.subject_name.lower()}|{self.object_name.lower()}|{self.direction}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


@dataclass
class ExtractedEntity:
    """translated note"""
    name: str
    entity_type: str
    aliases: List[str] = field(default_factory=list)
    attributes: Dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """translated note"""
    pmid: str
    title: str
    study_type: str
    claims: List[ExtractedClaim]
    entities: List[ExtractedEntity]
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


ALLOWED_EFFECT_DIRECTIONS = {
    "increased",
    "decreased",
    "changed",
    "no_significant_effect",
    "associated",
    "mixed",
    "unclear",
}

ALLOWED_HEALTH_INTERPRETATIONS = {
    "beneficial",
    "harmful",
    "neutral",
    "mixed",
    "unclear",
}


ADVERSE_OUTCOME_MARKERS = (
    "adverse",
    "body_mass_index",
    "chemotherapy_induced_diarrhea",
    "cholesterol",
    "constipation",
    "crp",
    "c_terminal_telopeptide",
    "depression",
    "diabetes",
    "diarrhea",
    "erythema",
    "fasting_serum_glucose",
    "glucose",
    "hba1c",
    "hs_crp",
    "homa",
    "inflammation",
    "insulin_resistance",
    "itching",
    "lesion",
    "nausea",
    "nec",
    "osteoporosis",
    "p_value",
    "parathyroid_hormone",
    "risk",
    "severity",
    "symptom",
    "triacylglycerol",
    "triglyceride",
    "vomiting",
    "waist_circumference",
    "white_spot",
)

BENEFICIAL_OUTCOME_MARKERS = (
    "antioxidant",
    "bifidobacteria",
    "bmd",
    "bone_mineral_density",
    "glutathione",
    "hdl",
    "lumbar_spine",
    "microbiota_diversity",
)

OUT_OF_SCOPE_SUBJECT_MARKERS = (
    "caffeine",
    "cell_free",
    "cell_free_supernatant",
    "traditional_chinese_herbal",
    "chinese_herbal",
    "herbal_decoction",
    "herbal_therapy",
    "neutralized_cell_free_supernatant",
    "neutralized_supernatant",
    "tcht",
)

IN_SCOPE_SUBJECT_MARKERS = (
    "actimel",
    "amazake",
    "bifidobacter",
    "cheese",
    "dahi",
    "dairy",
    "doogh",
    "ecologic",
    "ecologic_barrier",
    "ecologic_panda",
    "ecologicbarrier",
    "epi_7",
    "ferment_filtrate",
    "fermented",
    "fermented_milk_preparation",
    "fermented_soy",
    "fermented_soybean",
    "fortified_tempeh",
    "fortified_yogurt",
    "gaio",
    "human_milk_oligosaccharide",
    "ibp_9414",
    "fucosyllactose",
    "kefir",
    "kimchi",
    "kombucha",
    "lacto_n_neotetraose",
    "lab_diet",
    "lactic_acid_bacteria",
    "lactobac",
    "lactococcus",
    "lactiplantibacillus",
    "laal_dahi",
    "live_biotherapeutic",
    "malted_rice_amazake",
    "milk",
    "miso",
    "natto",
    "prebiotic",
    "probiotic",
    "postbiotic",
    "psychobiotic",
    "probio_eco",
    "saccharomyces",
    "sauerkraut",
    "starter_culture",
    "synbiotic",
    "tempeh",
    "vsl",
    "vsl3",
    "winclove",
    "weissella",
    "yeast",
    "zymomonas",
    "yogurt",
    "yoghurt",
)

OUT_OF_SCOPE_OUTCOME_MARKERS = (
    "acid_resilience",
    "acidic_resilience",
    "acid_resistance",
    "acid_tolerance",
    "acidic_challenge",
    "acidification_capacity",
    "acidification",
    "aggregation_and_adhesion",
    "aggregation_profile",
    "antimicrobial_activity_against",
    "antimicrobial_activity_zone",
    "antimicrobial_mechanism",
    "adhesion_profile",
    "acidic_stress_tolerance",
    "exopolysaccharide_production",
    "filamentous_fungi",
    "food_matrix",
    "gastrointestinal_tolerance",
    "innocua",
    "listeria_innocua",
    "osmotic_stress",
    "osmotic_tolerance",
    "osmotic_challenge",
    "pathogen_inhibition",
    "antagonistic_effect",
    "anti_staphylococcus",
    "antifungal_activity",
    "pseudomonas_aeruginosa",
    "aeruginosa",
    "quinoa_matrix",
    "riboflavin_production",
    "staphylococcus_inhibition",
    "starter_culture",
    "zone_of_inhibition",
)


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def infer_health_interpretation(effect_direction: str, outcome_name: str) -> str:
    """Infer health meaning when the LLM reports the measured direction only."""
    outcome = _normalized_text(outcome_name)
    if effect_direction == "no_significant_effect":
        return "neutral"
    if any(marker in outcome for marker in ADVERSE_OUTCOME_MARKERS):
        if effect_direction == "decreased":
            return "beneficial"
        if effect_direction == "increased":
            return "harmful"
    if any(marker in outcome for marker in BENEFICIAL_OUTCOME_MARKERS):
        if effect_direction == "increased":
            return "beneficial"
        if effect_direction == "decreased":
            return "harmful"
    return "unclear"


def normalize_legacy_direction(
    value: Any,
    effect_direction: str = "unclear",
    health_interpretation: str = "unclear",
    outcome_name: str = "",
) -> str:
    """Normalize the legacy positive/negative/neutral direction field."""
    normalized = _normalized_text(value)
    mapping = {
        "positive": "positive",
        "beneficial": "positive",
        "favorable": "positive",
        "improved": "positive",
        "negative": "negative",
        "harmful": "negative",
        "adverse": "negative",
        "deleterious": "negative",
        "neutral": "neutral",
        "no_effect": "neutral",
        "no_significant_effect": "neutral",
        "no_significant_difference": "neutral",
        "none": "",
        "null": "",
        "unknown": "",
        "unclear": "",
        "": "",
    }
    if effect_direction == "no_significant_effect" or health_interpretation == "neutral":
        return "neutral"
    if health_interpretation == "unclear" and outcome_name:
        health_interpretation = infer_health_interpretation(effect_direction, outcome_name)
    if health_interpretation == "beneficial":
        return "positive"
    if health_interpretation == "harmful":
        return "negative"
    direction = mapping.get(normalized, "")
    if direction:
        return direction
    return ""


def normalize_effect_direction(value: Any) -> str:
    """Map free-form measured-effect labels into the controlled schema."""
    normalized = _normalized_text(value)
    mapping = {
        "increase": "increased",
        "increases": "increased",
        "increased": "increased",
        "higher": "increased",
        "elevated": "increased",
        "decrease": "decreased",
        "decreases": "decreased",
        "decreased": "decreased",
        "reduced": "decreased",
        "reduction": "decreased",
        "lower": "decreased",
        "lowered": "decreased",
        "improved": "changed",
        "improvement": "changed",
        "enhanced": "increased",
        "enhancement": "increased",
        "impaired": "changed",
        "altered": "changed",
        "changed": "changed",
        "modulated": "changed",
        "no_effect": "no_significant_effect",
        "no_significant_effect": "no_significant_effect",
        "no_significant_difference": "no_significant_effect",
        "not_significant": "no_significant_effect",
        "neutral": "no_significant_effect",
        "associated": "associated",
        "association": "associated",
        "linked": "associated",
        "preferred": "associated",
        "mixed": "mixed",
        "unclear": "unclear",
        "unknown": "unclear",
        "": "unclear",
    }
    return mapping.get(normalized, normalized if normalized in ALLOWED_EFFECT_DIRECTIONS else "unclear")


def normalize_health_interpretation(value: Any) -> str:
    """Map free-form health/domain labels into the controlled schema."""
    normalized = _normalized_text(value)
    mapping = {
        "benefit": "beneficial",
        "beneficial": "beneficial",
        "positive": "beneficial",
        "favorable": "beneficial",
        "protective": "beneficial",
        "harm": "harmful",
        "harmful": "harmful",
        "negative": "harmful",
        "adverse": "harmful",
        "deleterious": "harmful",
        "neutral": "neutral",
        "no_effect": "neutral",
        "no_significant_effect": "neutral",
        "mixed": "mixed",
        "unclear": "unclear",
        "unknown": "unclear",
        "": "unclear",
    }
    return mapping.get(
        normalized,
        normalized if normalized in ALLOWED_HEALTH_INTERPRETATIONS else "unclear",
    )


def looks_like_non_result_snippet(text: str) -> bool:
    """Detect aim/method/background snippets that should not ground effect claims."""
    lowered = (text or "").lower()
    patterns = (
        "aimed to",
        "aims to",
        "designed to",
        "objective",
        "objectives",
        "the aim of",
        "the purpose of",
        "we investigated",
        "we examine",
        "examining the effects",
        "determine the effects",
        "was conducted to",
        "were randomly assigned",
        "participants were recruited",
        "this study investigated",
        "this trial",
    )
    return any(pattern in lowered for pattern in patterns)


def normalize_claim_subject_type(subject: str, subject_type: str) -> str:
    """Keep claim subjects in the graph schema even when the LLM says intervention."""
    normalized_type = _normalized_text(subject_type)
    subject_norm = _normalized_text(subject)
    strain_like_prefixes = (
        "bifidobacterium_",
        "lactobacillus_",
        "lactococcus_",
        "lactiplantibacillus_",
        "saccharomyces_",
        "weissella_",
    )
    if (
        subject_norm.startswith(strain_like_prefixes)
        and not any(marker in subject_norm for marker in ("+", "combination", "formulation", "supplement", "yogurt"))
    ):
        return "strain"
    if normalized_type in {"strain", "food"}:
        if normalized_type == "strain" and any(
            marker in subject_norm
            for marker in ("+", "combination", "formulation", "supplement", "yogurt")
        ):
            return "food"
        return normalized_type
    if normalized_type in {"intervention", "supplement", "treatment", "product", "formulation"}:
        return "food"
    if any(marker in subject_norm for marker in IN_SCOPE_SUBJECT_MARKERS):
        return "food"
    return normalized_type or "food"


def is_in_scope_subject(subject: str, subject_type: str) -> bool:
    """Reject clearly out-of-scope interventions while keeping core food/probiotic claims."""
    subject_norm = _normalized_text(subject)
    if any(marker in subject_norm for marker in OUT_OF_SCOPE_SUBJECT_MARKERS):
        return False
    if subject_type == "strain":
        return True
    return any(marker in subject_norm for marker in IN_SCOPE_SUBJECT_MARKERS)


def is_in_scope_claim(subject: str, subject_type: str, outcome: str) -> bool:
    """Keep food/probiotic health claims; reject product-process and lab assay claims."""
    if not is_in_scope_subject(subject, subject_type):
        return False
    outcome_norm = _normalized_text(outcome)
    return not any(marker in outcome_norm for marker in OUT_OF_SCOPE_OUTCOME_MARKERS)


# V3 Prompts - translated note,translated note

V3_REVIEW_PROMPT = """You are an expert health-science knowledge extraction specialist.
Extract structured knowledge from the following review article. All output must be in English.

Article information:
- PMID: {pmid}
- Title: {title}
- Abstract: {abstract}

## Extraction Tasks

### 1. Entity Recognition
Identify key entities mentioned in the article:

A. Foods / fermented foods:
   - Use English names only
   - Examples: yogurt, kefir, kimchi

B. Probiotic strains:
   - **Strict requirement**: must be a valid Latin binomial
   - Valid format: "Lactobacillus rhamnosus GG"
   - **Invalid**: "probiotics", "fermented foods" or other non-specific names

C. Health outcome measures:
   - Specific indicators, e.g. "blood_glucose", "cholesterol", "gut_microbiota"

### 2. Effect Claims — core output
Extract each important health-effect claim from the article.
Extract only reported findings, conclusions, or evidence-backed effects.
Do not extract study aims, objectives, background rationale, group assignment,
or methods as effect claims.

For each claim, provide:
- subject: the intervention (food name, probiotic/synbiotic product, or strain name)
- subject_type: "food" or "strain"; use "food" for probiotic/synbiotic supplementation, formulations, products, blends, or multi-strain combinations
- outcome: the health outcome
- **direction: legacy overall direction (must be: positive / negative / neutral)**
- **effect_direction: measured outcome direction (must be: increased / decreased / changed / no_significant_effect / associated / mixed / unclear)**
- **health_interpretation: health/domain meaning (must be: beneficial / harmful / neutral / mixed / unclear)**
- evidence_strength: "strong" / "moderate" / "weak"
- key_finding: concise English summary of the finding
- evidence_snippet: verbatim sentence from the abstract that directly supports the claim
- dose: dosage information (if reported)

### 3. Output Format (JSON)

```json
{{
  "entities": {{
    "foods": [{{"name": "yogurt", "category": "fermented_dairy"}}],
    "strains": [{{"name": "Lactobacillus rhamnosus GG", "genus": "Lactobacillus", "species": "rhamnosus"}}],
    "outcomes": [{{"name": "blood_glucose", "category": "metabolic"}}]
  }},
  "claims": [
    {{
      "subject": "yogurt",
      "subject_type": "food",
      "outcome": "blood_glucose",
      "direction": "positive",
      "effect_direction": "decreased",
      "health_interpretation": "beneficial",
      "evidence_strength": "moderate",
      "key_finding": "Yogurt consumption is associated with reduced blood glucose levels",
      "evidence_snippet": "Verbatim abstract sentence supporting the yogurt and blood glucose claim.",
      "dose": "200 g/day"
    }}
  ],
  "confidence": "high"
}}
```

**Constraints**:
1. direction must be exactly one of: positive / negative / neutral
2. effect_direction must describe the measured outcome change, not whether the change is good or bad
3. health_interpretation must describe the domain/health meaning; use unclear when the abstract does not justify it
4. Strains must be valid Latin binomials
5. All food names and outcome names must be in English
6. Do not fabricate data
7. evidence_snippet must be copied from the abstract; use an empty string only if no direct supporting sentence exists
8. effect_direction must be exactly one of: increased / decreased / changed / no_significant_effect / associated / mixed / unclear
9. Do not use words such as improved, reduced, impaired, preferred, enhanced, or lowered in effect_direction; map them to the controlled labels above
10. Do not create a claim from an aim/objective/method/background sentence
11. Do not use subject_type values such as intervention, supplement, treatment, or product
12. Exclude clearly out-of-scope interventions such as caffeine or non-food herbal therapies unless they are fermented food/probiotic/synbiotic interventions
"""


V3_PRIMARY_PROMPT = """You are an expert health-science knowledge extraction specialist.
Extract structured knowledge from the following primary research article. All output must be in English.

Article information:
- PMID: {pmid}
- Title: {title}
- Abstract: {abstract}

## Extraction Tasks

### 1. Entity Recognition
A. Foods: name, category; include probiotic/synbiotic supplements, formulations, blends, and fortified yogurt products here
B. Probiotic strains: full Latin binomial
C. Outcome measures: specific health indicators

### 2. Statistical Results — priority output
For each primary outcome:
Extract only reported results or conclusions, not study aims, trial design,
background rationale, intervention assignment, or endpoints listed without
results.
- subject: the intervention (food, probiotic/synbiotic product, or strain)
- subject_type: "food" or "strain"; use "food" for probiotic/synbiotic supplementation, formulations, products, blends, or multi-strain combinations
- outcome: outcome measure
- **direction: legacy overall direction, positive / negative / neutral (required)**
- **effect_direction: measured outcome direction (increased / decreased / changed / no_significant_effect / associated / mixed / unclear)**
- **health_interpretation: health/domain meaning (beneficial / harmful / neutral / mixed / unclear)**
- effect_size: numeric value (e.g. "-0.5%", "SMD -0.45")
- confidence_interval: 95% CI
- p_value: e.g. "<0.01", "=0.03"
- key_finding: concise English summary of the finding
- evidence_snippet: verbatim sentence from the abstract that directly supports the claim
- dose: e.g. "10^9 CFU/day"
- duration: e.g. "8 weeks"

### 3. Output Format (JSON)

```json
{{
  "entities": {{
    "foods": [{{"name": "probiotic_yogurt", "category": "fermented_dairy"}}],
    "strains": [{{"name": "Lactobacillus rhamnosus GG", "genus": "Lactobacillus", "species": "rhamnosus"}}],
    "outcomes": [{{"name": "HbA1c", "category": "metabolic"}}]
  }},
  "claims": [
    {{
      "subject": "probiotic_yogurt",
      "subject_type": "food",
      "outcome": "HbA1c",
      "direction": "positive",
      "effect_direction": "decreased",
      "health_interpretation": "beneficial",
      "effect_size": "-0.5%",
      "confidence_interval": "-0.8 to -0.2",
      "p_value": "<0.01",
      "key_finding": "Probiotic yogurt decreased HbA1c compared with control",
      "evidence_snippet": "Verbatim abstract sentence supporting the probiotic yogurt and HbA1c claim.",
      "dose": "200 g/day",
      "duration": "8 weeks"
    }}
  ]
}}
```

**Constraints**:
1. direction must be explicitly chosen
2. effect_direction must describe the measured outcome change, not whether the change is good or bad
3. health_interpretation must describe the health/domain meaning; use unclear when the abstract does not justify it
4. Numeric values must be extracted from the text; do not fabricate
5. If a value is not reported, use null
6. evidence_snippet must be copied verbatim from the abstract; use an empty string only if no direct supporting sentence exists
7. effect_direction must be exactly one of: increased / decreased / changed / no_significant_effect / associated / mixed / unclear
8. Do not use words such as improved, reduced, impaired, preferred, enhanced, or lowered in effect_direction; map them to the controlled labels above
9. Do not create a claim from an aim/objective/method/background sentence
10. Do not use subject_type values such as intervention, supplement, treatment, or product
11. Exclude clearly out-of-scope interventions such as caffeine or non-food herbal therapies unless they are fermented food/probiotic/synbiotic interventions
"""


V3_ZERO_CLAIM_RETRY_PROMPT = """You are repairing a zero-claim extraction for the Food-AI knowledge graph.
The first pass found no claims. Extract claims from the candidate result sentences below.

Article information:
- PMID: {pmid}
- Study type: {study_type}
- Title: {title}
- Abstract: {abstract}

Candidate result sentences:
{candidate_sentences}

In-scope subjects:
- fermented foods and dairy products such as yogurt, kefir, cheese, fermented milk
- probiotic, prebiotic, or synbiotic supplements/products/formulations/blends
- valid probiotic strains, yeasts, or starter cultures when tied to a health or probiotic-property outcome
- fortified yogurt or fermented dairy products

Out-of-scope subjects:
- caffeine, generic exercise supplements, and non-food herbal therapies
- broad intervention classes that are not fermented food/probiotic/synbiotic
- study aims, objectives, background, design, assignment, or methods

For meta-analyses/reviews, extract reported pooled or ranked results from the candidate result sentences.
For primary trials, extract reported statistically clear results and clearly stated no-effect outcomes from the candidate result sentences.

Return strict JSON only:
{{
  "entities": {{
    "foods": [{{"name": "probiotic supplement", "category": "probiotic"}}],
    "strains": [],
    "outcomes": [{{"name": "fasting_plasma_glucose", "category": "metabolic"}}]
  }},
  "claims": [
    {{
      "subject": "probiotic supplement",
      "subject_type": "food",
      "outcome": "fasting_plasma_glucose",
      "direction": "positive",
      "effect_direction": "decreased",
      "health_interpretation": "beneficial",
      "effect_size": null,
      "confidence_interval": null,
      "p_value": null,
      "evidence_strength": "moderate",
      "key_finding": "Probiotic supplementation decreased fasting plasma glucose",
      "evidence_snippet": "Verbatim abstract sentence directly supporting this claim.",
      "dose": null,
      "duration": null
    }}
  ],
  "confidence": "medium"
}}

Rules:
1. subject_type must be exactly food or strain; use food for probiotic/synbiotic supplementation, products, blends, formulations, and multi-strain combinations
2. direction must be positive, negative, or neutral
3. effect_direction must be increased, decreased, changed, no_significant_effect, associated, mixed, or unclear
4. health_interpretation must be beneficial, harmful, neutral, mixed, or unclear
5. evidence_snippet must be copied verbatim from the abstract
6. Return an empty claims list only if all candidate result sentences are truly out-of-scope or unsupported
"""


class V3EntityNormalizer:
    """V3 translated note - translated note + LLM translated note"""

    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.entity_index = {}  # entity_type -> {canonical_name: entity_data}
        self.entity_embeddings = defaultdict(dict)  # entity_type -> {canonical_name: embedding}
        self.food_normalizer = FoodNameNormalizer()
        self.strain_validator = StrainValidator()
        self.embedding_client = get_embedding_client()
        self.llm_merge_enabled = os.getenv("FOOD_AI_ENTITY_MERGE_LLM", "1").lower() not in {"0", "false", "no"}
        self.llm_merge_max_checks = int(os.getenv("FOOD_AI_ENTITY_MERGE_LLM_MAX_CHECKS", "60"))
        self.embedding_merge_threshold = float(os.getenv("FOOD_AI_ENTITY_MERGE_EMBEDDING_THRESHOLD", "0.88"))
        self.stats = {
            "exact_matches": 0,
            "embedding_merges": 0,
            "llm_merge_checks": 0,
            "new_entities": 0,
        }

    def normalize_entity(self, name: str, entity_type: str,
                         existing_entities: Dict = None) -> Tuple[str, List[str]]:
        """
        translated note

        Returns:
            (canonical_name, aliases)
        """
        if not name:
            return "", []

        # 1. translated note
        name_lower = name.lower().strip()

        # 2. translated note
        if entity_type == "food":
            canonical = self.food_normalizer.normalize(name)
            aliases = self._generate_aliases(name)
        elif entity_type == "strain":
            result = self.strain_validator.validate(name)
            if result.is_valid:
                canonical = result.normalized_name
                aliases = [name, result.normalized_name]
            else:
                canonical = name_lower.replace(" ", "_")
                aliases = [name]
        else:
            canonical = name_lower.replace(" ", "_")
            aliases = [name]

        matched = self._find_exact_match(canonical, entity_type)
        if matched:
            self._register_entity(matched, entity_type, aliases)
            self.stats["exact_matches"] += 1
            return matched, aliases

        if entity_type in {"food", "outcome"}:
            candidates = self._recall_candidates(canonical, entity_type, top_k=3)
            for candidate_name, score, reason in candidates:
                if self._should_merge_with_candidate(canonical, candidate_name, entity_type, score, reason):
                    self._register_entity(candidate_name, entity_type, aliases)
                    self.stats["embedding_merges"] += 1
                    return candidate_name, aliases

        self._register_entity(canonical, entity_type, aliases)
        self.stats["new_entities"] += 1
        return canonical, aliases

    def _generate_aliases(self, name: str) -> List[str]:
        """translated note"""
        aliases = [name]
        name_lower = name.lower()

        # translated note
        alias_rules = {
            "yogurt": ["yoghurt"],
            "kefir": ["kephir"],
            "kimchi": ["kimchee"],
            "kombucha": ["combucha"],
        }

        if name_lower in alias_rules:
            aliases.extend(alias_rules[name_lower])

        return list(set(aliases))

    def find_similar_entity(self, name: str, entity_type: str,
                           threshold: float = 0.8) -> Optional[str]:
        """
        translated note
        translated note:translated note,translated note
        """
        name_lower = name.lower().replace(" ", "_")

        if entity_type not in self.entity_index:
            return None

        for canonical_name, entity_data in self.entity_index[entity_type].items():
            # translated note
            if name_lower == canonical_name.lower():
                return canonical_name

            # translated note
            aliases = entity_data.get("aliases", [])
            for alias in aliases:
                if name_lower == alias.lower().replace(" ", "_"):
                    return canonical_name

            # translated note(translated note)
            if name_lower in canonical_name.lower() or canonical_name.lower() in name_lower:
                return canonical_name

        return None

    def total_registered_entities(self) -> int:
        return sum(len(items) for items in self.entity_index.values())

    def _find_exact_match(self, canonical: str, entity_type: str) -> Optional[str]:
        if entity_type not in self.entity_index:
            return None

        normalized = canonical.lower().replace(" ", "_")
        for existing_name, entity_data in self.entity_index[entity_type].items():
            existing_normalized = existing_name.lower().replace(" ", "_")
            if normalized == existing_normalized:
                return existing_name

            for alias in entity_data.get("aliases", []):
                alias_normalized = alias.lower().replace(" ", "_")
                if normalized == alias_normalized:
                    return existing_name
        return None

    def _register_entity(self, canonical: str, entity_type: str, aliases: List[str]) -> None:
        if not canonical:
            return

        entity_bucket = self.entity_index.setdefault(entity_type, {})
        existing = entity_bucket.get(canonical, {"aliases": [], "name": canonical})
        merged_aliases = set(existing.get("aliases", []))
        merged_aliases.update(alias for alias in aliases if alias)
        merged_aliases.add(canonical)
        existing["aliases"] = sorted(merged_aliases)
        entity_bucket[canonical] = existing

        if entity_type in {"food", "outcome"} and canonical not in self.entity_embeddings[entity_type]:
            vector = self.embedding_client.embed(canonical.replace("_", " "))
            if vector:
                self.entity_embeddings[entity_type][canonical] = vector

    def _recall_candidates(self, canonical: str, entity_type: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        candidates: List[Tuple[str, float, str]] = []
        if entity_type not in self.entity_index or not self.entity_index[entity_type]:
            return candidates

        lexical_scored = []
        for existing_name in self.entity_index[entity_type]:
            score = self._lexical_similarity(canonical, existing_name)
            if score >= 0.45:
                lexical_scored.append((existing_name, score, "lexical"))
        lexical_scored.sort(key=lambda item: item[1], reverse=True)

        vector = self.embedding_client.embed(canonical.replace("_", " "))
        if vector and self.entity_embeddings.get(entity_type):
            embedding_scored = []
            for existing_name, existing_vector in self.entity_embeddings[entity_type].items():
                score = self._cosine_similarity(vector, existing_vector)
                if score >= self.embedding_merge_threshold:
                    embedding_scored.append((existing_name, score, "embedding"))
            embedding_scored.sort(key=lambda item: item[1], reverse=True)
            if embedding_scored:
                return embedding_scored[:top_k]

        return lexical_scored[:top_k]

    def _should_merge_with_candidate(
        self,
        canonical: str,
        candidate_name: str,
        entity_type: str,
        score: float,
        reason: str,
    ) -> bool:
        if reason == "lexical" and score >= 0.92:
            return True
        if score < self.embedding_merge_threshold:
            return False
        if not self.llm_merge_enabled:
            return False
        if self.stats["llm_merge_checks"] >= self.llm_merge_max_checks:
            return False

        self.stats["llm_merge_checks"] += 1
        prompt = f"""You are deciding whether two entity names in a food-health knowledge graph should map to the same canonical entity.

Entity type: {entity_type}
Candidate A: {canonical}
Candidate B: {candidate_name}
Similarity source: {reason}
Similarity score: {score:.4f}

Return strict JSON:
{{
  "same_entity": true or false,
  "reasoning": "short explanation"
}}

Rules:
- Return true only if they refer to the same canonical entity in this graph layer.
- Variants that should remain distinct exposures must return false.
- Broader vs narrower concepts should usually return false.
"""
        try:
            result = self.llm.extract_json(prompt, "You make conservative canonicalization decisions.")
            return bool(result.get("same_entity"))
        except Exception:
            return False

    def _lexical_similarity(self, left: str, right: str) -> float:
        left_tokens = set(left.lower().split("_"))
        right_tokens = set(right.lower().split("_"))
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if left in right or right in left:
            overlap = max(overlap, 0.75)
        return overlap

    def _cosine_similarity(self, left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)


class V3ClaimMerger:
    """V3 Claim translated note"""

    def __init__(self, llm_client=None):
        self.llm = llm_client or get_llm_client()
        self.claims_index = {}  # claim_id -> claim_data

    def generate_claim_id(self, subject: str, obj: str, direction: str) -> str:
        """translated note claim translated note ID"""
        key = f"{subject.lower()}|{obj.lower()}|{direction}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def try_merge_claim(self, new_claim: Dict) -> Tuple[str, bool]:
        """
        translated note claim

        Returns:
            (claim_id, is_new)
        """
        subject = new_claim.get("subject", "")
        obj = new_claim.get("object", "")
        direction = new_claim.get("direction", "neutral")

        claim_id = self.generate_claim_id(subject, obj, direction)

        if claim_id in self.claims_index:
            # translated note,translated note evidence
            existing = self.claims_index[claim_id]
            self._merge_evidence(existing, new_claim)
            return claim_id, False
        else:
            # translated note claim
            self.claims_index[claim_id] = self._create_claim_node(claim_id, new_claim)
            return claim_id, True

    def _create_claim_node(self, claim_id: str, raw_claim: Dict) -> Dict:
        """translated note claim translated note"""
        return {
            "node_type": "claim",
            "claim_id": claim_id,
            "claim_text": (
                f"{raw_claim.get('subject')} has {raw_claim.get('direction')} effect "
                f"on {raw_claim.get('object')}"
            ),

            "subject_type": raw_claim.get("subject_type", "food"),
            "subject_name": raw_claim.get("subject", ""),

            "object_type": raw_claim.get("object_type", "outcome"),
            "object_name": raw_claim.get("object", ""),

            "direction": raw_claim.get("direction", "neutral"),
            "effect_direction": raw_claim.get("effect_direction", "unclear"),
            "health_interpretation": raw_claim.get("health_interpretation", "unclear"),

            # translated note
            "dose_info": {
                "value": raw_claim.get("dose"),
                "unit": None,
                "duration": raw_claim.get("duration")
            } if raw_claim.get("dose") else None,

            # Evidence translated note
            "evidence_list": [self._extract_evidence(raw_claim)],
            "evidence_count": 1,

            "confidence_score": self._calculate_confidence(raw_claim),

            "merged_from": [raw_claim.get("original_key", "")],
            "first_seen": raw_claim.get("pmid", ""),
            "last_updated": raw_claim.get("pmid", "")
        }

    def _merge_evidence(self, existing_claim: Dict, new_claim: Dict):
        """translated note evidence translated note claim"""
        new_evidence = self._extract_evidence(new_claim)

        existing_claim.setdefault("evidence_list", []).append(new_evidence)
        existing_claim["evidence_count"] = len(existing_claim["evidence_list"])
        existing_claim.setdefault("merged_from", []).append(new_claim.get("original_key", ""))
        existing_claim["last_updated"] = new_claim.get("pmid", "")

        # translated note
        existing_claim["confidence_score"] = self._recalculate_confidence(
            existing_claim["evidence_list"]
        )

    def _extract_evidence(self, claim_data: Dict) -> Dict:
        """translated note claim translated note evidence translated note"""
        return {
            "pmid": claim_data.get("pmid", ""),
            "study_type": claim_data.get("study_type", ""),
            "effect_size": claim_data.get("effect_size"),
            "p_value": claim_data.get("p_value"),
            "confidence_interval": claim_data.get("confidence_interval"),
            "key_finding": claim_data.get("key_finding", ""),
            "evidence_snippet": claim_data.get("evidence_snippet", ""),
            "effect_direction": claim_data.get("effect_direction", "unclear"),
            "health_interpretation": claim_data.get("health_interpretation", "unclear"),
            "population": claim_data.get("population", ""),
            "confidence": claim_data.get("confidence", "medium")
        }

    def _calculate_confidence(self, claim_data: Dict) -> float:
        """translated note claim translated note"""
        score = 0.5  # translated note

        # translated note
        if claim_data.get("effect_size"):
            score += 0.1

        # translated note p translated note
        p_value = claim_data.get("p_value", "")
        if p_value and ("<0.01" in str(p_value) or "<0.05" in str(p_value)):
            score += 0.1

        # translated note
        study_type = claim_data.get("study_type", "").lower()
        if "rct" in study_type or "meta" in study_type:
            score += 0.2
        elif "review" in study_type:
            score += 0.1

        return min(score, 1.0)

    def _recalculate_confidence(self, evidence_list: List[Dict]) -> float:
        """translated note evidence translated note"""
        # translated note
        count_bonus = min(len(evidence_list) * 0.1, 0.3)

        # translated note
        study_types = set(e.get("study_type", "").lower() for e in evidence_list)
        diversity_bonus = min(len(study_types) * 0.05, 0.2)

        # translated note(translated note)
        base_scores = []
        for ev in evidence_list:
            base_score = 0.5
            if ev.get("effect_size"):
                base_score += 0.1
            if ev.get("p_value"):
                base_score += 0.1
            base_scores.append(base_score)

        avg_base = sum(base_scores) / len(base_scores) if base_scores else 0.5

        return min(avg_base + count_bonus + diversity_bonus, 1.0)

    def get_all_claims(self) -> List[Dict]:
        """translated note claims"""
        return list(self.claims_index.values())


class EnhancedExtractorV3:
    """V3 translated note - Claim-Centric translated note"""

    def __init__(self):
        self.llm = get_llm_client()
        self.entity_normalizer = V3EntityNormalizer(self.llm)
        self.claim_merger = V3ClaimMerger(self.llm)
        self.validator = EntityValidator()

    def extract(self, article: Dict[str, Any], study_type: str) -> ExtractionResult:
        """
        translated note:translated note
        """
        pmid = article.get('pmid', '')
        title = article.get('title', '')
        normalized_study_type = self._normalize_study_type(article, study_type)

        try:
            warnings = []
            # 1. LLM translated note
            raw_result = self._llm_extract(article, normalized_study_type)
            zero_retry_attempted = False
            if not raw_result.get('claims') and self._should_retry_zero_claim(article):
                retry_result = self._llm_extract_zero_claim_retry(article, normalized_study_type)
                zero_retry_attempted = True
                if retry_result.get('claims'):
                    raw_result = retry_result
                    warnings.append(
                        f"Used zero-claim retry for PMID {pmid}: "
                        f"{len(retry_result.get('claims', []))} raw claims"
                    )

            # 2. translated note
            entities, entity_warnings = self._normalize_entities(raw_result.get('entities', {}))
            warnings.extend(entity_warnings)

            # 3. translated note Claims(translated note + translated note)
            claims, claim_warnings = self._process_claims(
                raw_result.get('claims', []),
                entities,
                pmid,
                normalized_study_type
            )
            warnings.extend(claim_warnings)
            if not claims and not zero_retry_attempted and self._should_retry_zero_claim(article):
                retry_result = self._llm_extract_zero_claim_retry(article, normalized_study_type)
                if retry_result.get('claims'):
                    retry_entities, retry_entity_warnings = self._normalize_entities(
                        retry_result.get('entities', {})
                    )
                    retry_claims, retry_claim_warnings = self._process_claims(
                        retry_result.get('claims', []),
                        retry_entities,
                        pmid,
                        normalized_study_type,
                    )
                    if retry_claims:
                        entities = retry_entities
                        claims = retry_claims
                        warnings.append(
                            f"Used zero-claim retry after post-processing for PMID {pmid}: "
                            f"{len(retry_claims)} claims"
                        )
                        warnings.extend(retry_entity_warnings)
                        warnings.extend(retry_claim_warnings)
            if not claims and self._should_retry_zero_claim(article):
                rule_result = self._rule_based_zero_claim_retry(
                    self._candidate_result_sentences(article.get('abstract', ''))
                )
                if rule_result.get('claims'):
                    rule_entities, rule_entity_warnings = self._normalize_entities(
                        rule_result.get('entities', {})
                    )
                    rule_claims, rule_claim_warnings = self._process_claims(
                        rule_result.get('claims', []),
                        rule_entities,
                        pmid,
                        normalized_study_type,
                    )
                    if rule_claims:
                        entities = rule_entities
                        claims = rule_claims
                        warnings.append(
                            f"Used rule-based zero-claim retry for PMID {pmid}: "
                            f"{len(rule_claims)} claims"
                        )
                        warnings.extend(rule_entity_warnings)
                        warnings.extend(rule_claim_warnings)

            return ExtractionResult(
                pmid=pmid,
                title=title,
                study_type=normalized_study_type,
                claims=claims,
                entities=entities,
                success=True,
                warnings=warnings,
            )

        except Exception as e:
            return ExtractionResult(
                pmid=pmid,
                title=title,
                study_type=normalized_study_type,
                claims=[],
                entities=[],
                success=False,
                errors=[str(e)]
            )

    def _normalize_study_type(self, article: Dict[str, Any], study_type: str) -> str:
        """Repair coarse upstream study type labels using title/abstract cues."""
        title = (article.get('title') or '').lower()
        abstract = (article.get('abstract') or '').lower()
        text = f"{title}\n{abstract}"
        source = (study_type or '').lower()

        review_markers = [
            'meta-analysis',
            'systematic review',
            'network meta-analysis',
            'umbrella review',
            'scoping review',
        ]
        if any(marker in text for marker in review_markers):
            return 'review'
        if ' review' in text or title.endswith('review'):
            return 'review'

        primary_markers = [
            'randomized',
            'randomised',
            'clinical trial',
            'double-blind',
            'placebo-controlled',
            'crossover',
        ]
        if any(marker in text for marker in primary_markers):
            return 'RCT' if 'crossover' not in text else 'Crossover trial'

        if source in {'review', 'meta-analysis/review'}:
            return 'review'
        return study_type

    def _llm_extract(self, article: Dict, study_type: str) -> Dict:
        """translated note LLM translated note"""
        pmid = article.get('pmid', '')
        title = article.get('title', '')
        abstract = article.get('abstract', '')

        # translated note Prompt
        if study_type == 'review':
            prompt = V3_REVIEW_PROMPT.format(
                pmid=pmid,
                title=title,
                abstract=abstract[:3000] if abstract else "N/A"
            )
        else:
            prompt = V3_PRIMARY_PROMPT.format(
                pmid=pmid,
                title=title,
                abstract=abstract[:3000] if abstract else "N/A"
            )

        result = self.llm.extract_json(prompt, "translated note.")
        return result

    def _should_retry_zero_claim(self, article: Dict[str, Any]) -> bool:
        text = _normalized_text(
            f"{article.get('title', '')} {article.get('abstract', '')}"
        )
        if any(marker in text for marker in OUT_OF_SCOPE_SUBJECT_MARKERS):
            return False
        return any(marker in text for marker in IN_SCOPE_SUBJECT_MARKERS)

    def _llm_extract_zero_claim_retry(self, article: Dict[str, Any], study_type: str) -> Dict:
        """Focused second pass for likely in-scope abstracts that returned no claims."""
        candidate_sentences = self._candidate_result_sentences(article.get('abstract', ''))
        if not candidate_sentences:
            return {"entities": {}, "claims": []}
        prompt = V3_ZERO_CLAIM_RETRY_PROMPT.format(
            pmid=article.get('pmid', ''),
            study_type=study_type,
            title=article.get('title', ''),
            abstract=(article.get('abstract', '') or "N/A")[:3000],
            candidate_sentences="\n".join(
                f"- {sentence}" for sentence in candidate_sentences[:10]
            ),
        )
        last_result: Dict[str, Any] = {"entities": {}, "claims": []}
        for _ in range(3):
            try:
                result = self.llm.extract_json(
                    prompt,
                    "translated note claims.",
                    temperature=0,
                )
                if result.get('claims'):
                    return result
                last_result = result
            except Exception:
                continue
        rule_result = self._rule_based_zero_claim_retry(candidate_sentences)
        return rule_result if rule_result.get('claims') else last_result

    def _candidate_result_sentences(self, abstract: str) -> List[str]:
        """Pick likely result-bearing sentences for focused zero-claim repair."""
        if not abstract:
            return []
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', abstract.strip())
        result_markers = (
            "95% ci",
            "achieved",
            "associated with",
            "compared with",
            "compared to",
            "decreased",
            "did not",
            "existed",
            "found on",
            "greatest reduction",
            "improved",
            "increase",
            "increased",
            "lower",
            "lowered",
            "md",
            "no increase",
            "no significant",
            "observed",
            "odds ratio",
            "p ",
            "p<",
            "p =",
            "p ",
            "reduced",
            "reduction",
            "risk ratio",
            "rr:",
            "significant",
            "smd",
        )
        candidates = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(marker in lowered for marker in result_markers):
                candidates.append(sentence.strip())
        return candidates

    def _rule_based_zero_claim_retry(self, candidate_sentences: List[str]) -> Dict[str, Any]:
        """Narrow deterministic fallback for explicit result sentences."""
        outcome_aliases = {
            "fasting_plasma_glucose": ("fasting plasma glucose", "fpg"),
            "hba1c": ("hba1c", "hemoglobin a1c"),
            "total_cholesterol": ("total cholesterol",),
            "lumbar_spine_bone_mineral_density": ("lumbar spine bone mineral density", "lumbar spine bmd"),
            "parathyroid_hormone": ("parathyroid hormone",),
            "adverse_events": ("adverse event", "adverse reaction"),
            "total_hip_bone_mineral_density": ("total hip bmd", "total hip bone mineral density"),
            "osteocalcin": ("osteocalcin",),
            "c_terminal_telopeptide": ("c-terminal telopeptide",),
            "alkaline_phosphatase": ("alkaline phosphatase",),
            "osteoprotegerin": ("osteoprotegerin",),
            "depression_symptoms": ("beck depression inventory", "depression"),
            "serum_insulin": ("serum insulin", "insulin levels"),
            "insulin_resistance": ("insulin resistance", "homa-ir", "homeostasis model assessment of insulin resistance"),
            "hs_crp": ("hs-crp", "c-reactive protein"),
            "glutathione": ("glutathione",),
            "fasting_plasma_glucose_no_effect": ("fasting plasma glucose",),
            "diarrhea": ("diarrhea",),
            "constipation": ("constipation",),
            "nausea": ("nausea",),
            "vomiting": ("vomiting",),
        }
        claims = []
        foods = set()
        outcomes = set()
        seen_claims = set()
        for sentence in candidate_sentences:
            if looks_like_non_result_snippet(sentence):
                continue
            lowered = sentence.lower()
            subject = self._infer_retry_subject(lowered)
            if not subject:
                continue
            for outcome, aliases in outcome_aliases.items():
                if not any(alias in lowered for alias in aliases):
                    continue
                canonical_outcome = outcome.replace("_no_effect", "")
                direction = "positive"
                effect_direction = "changed"
                health_interpretation = "beneficial"
                if "no significant" in lowered or "no increase" in lowered or "did not" in lowered:
                    direction = "neutral"
                    effect_direction = "no_significant_effect"
                    health_interpretation = "neutral"
                elif any(marker in lowered for marker in ("decrease", "decreased", "decreases", "reduced", "reduction", "lower", "lowered", "md = -", "md = -", "smd: -")):
                    effect_direction = "decreased"
                    health_interpretation = infer_health_interpretation(effect_direction, canonical_outcome)
                    if health_interpretation == "unclear":
                        health_interpretation = "beneficial"
                elif any(marker in lowered for marker in ("increased", "improved", "rise", "smd: 0.", "smd: 1.", "smd 0.", "smd 1.")):
                    effect_direction = "increased"
                    health_interpretation = infer_health_interpretation(effect_direction, canonical_outcome)
                    if health_interpretation == "unclear":
                        health_interpretation = "beneficial"
                claim_key = (subject.lower(), canonical_outcome)
                if claim_key in seen_claims:
                    continue
                seen_claims.add(claim_key)
                foods.add(subject)
                outcomes.add(canonical_outcome)
                claims.append({
                    "subject": subject,
                    "subject_type": "food",
                    "outcome": canonical_outcome,
                    "direction": direction,
                    "effect_direction": effect_direction,
                    "health_interpretation": health_interpretation,
                    "effect_size": None,
                    "confidence_interval": None,
                    "p_value": self._extract_p_value(sentence),
                    "evidence_strength": "moderate",
                    "key_finding": sentence,
                    "evidence_snippet": sentence,
                    "dose": None,
                    "duration": None,
                })
        return {
            "entities": {
                "foods": [{"name": name, "category": "probiotic"} for name in sorted(foods)],
                "strains": [],
                "outcomes": [{"name": name, "category": "other"} for name in sorted(outcomes)],
            },
            "claims": claims[:12],
            "confidence": "medium",
        }

    def _infer_retry_subject(self, lowered_sentence: str) -> str:
        if "lactocare" in lowered_sentence:
            return "LactoCare synbiotic"
        if "probiotic/synbiotic" in lowered_sentence:
            return "probiotic synbiotic supplement"
        if "probiotic supplements" in lowered_sentence or "probiotic supplementation" in lowered_sentence:
            return "probiotic supplement"
        if "combination of bifidobacterium" in lowered_sentence or "multi-strain" in lowered_sentence:
            return "multi strain probiotic formulation"
        if "yogurt containing" in lowered_sentence:
            return "probiotic yogurt"
        if "yeast containing saccharomyces cerevisiae" in lowered_sentence:
            return "saccharomyces cerevisiae yeast"
        if "probiotic" in lowered_sentence:
            return "probiotic supplement"
        if "synbiotic" in lowered_sentence:
            return "synbiotic supplement"
        return ""

    def _extract_p_value(self, sentence: str) -> Optional[str]:
        match = re.search(r'P\s*[=<>]\s*0?\.\d+', sentence, flags=re.IGNORECASE)
        return match.group(0) if match else None

    def _normalize_entities(self, entities: Dict) -> Tuple[List[ExtractedEntity], List[str]]:
        """translated note"""
        normalized = []
        warnings = []

        # translated note Foods
        for food in entities.get('foods', []):
            name = food.get('name', '')
            if name:
                validation = self.validator.validate_food_name(name)
                if not validation.is_valid:
                    warnings.append(f"Skipped suspicious food entity '{name}': {'; '.join(validation.errors)}")
                    continue
                canonical, aliases = self.entity_normalizer.normalize_entity(name, 'food')
                normalized.append(ExtractedEntity(
                    name=canonical,
                    entity_type='food',
                    aliases=aliases,
                    attributes={'category': food.get('category', 'unknown')}
                ))

        # translated note Strains
        for strain in entities.get('strains', []):
            name = strain.get('name', '')
            if name:
                canonical, aliases = self.entity_normalizer.normalize_entity(name, 'strain')
                normalized.append(ExtractedEntity(
                    name=canonical,
                    entity_type='strain',
                    aliases=aliases,
                    attributes={
                        'genus': strain.get('genus', ''),
                        'species': strain.get('species', '')
                    }
                ))

        # translated note Outcomes
        for outcome in entities.get('outcomes', []):
            name = outcome.get('name', '')
            if name:
                canonical, aliases = self.entity_normalizer.normalize_entity(name, 'outcome')
                normalized.append(ExtractedEntity(
                    name=canonical,
                    entity_type='outcome',
                    aliases=aliases,
                    attributes={'category': outcome.get('category', 'other')}
                ))

        return normalized, warnings

    def _process_claims(self, raw_claims: List[Dict], entities: List[ExtractedEntity],
                       pmid: str, study_type: str) -> Tuple[List[ExtractedClaim], List[str]]:
        """translated note claims(translated note + translated note)"""
        processed = []
        warnings = []

        # translated note
        entity_map = {e.name: e for e in entities}

        for raw_claim in raw_claims:
            # translated note
            subject = raw_claim.get('subject', '')
            subject_type = normalize_claim_subject_type(
                subject,
                raw_claim.get('subject_type', 'food'),
            )
            if subject_type not in {"food", "strain"}:
                warnings.append(
                    f"Skipped claim for PMID {pmid}: unsupported subject type "
                    f"'{raw_claim.get('subject_type')}' for '{subject}'"
                )
                continue
            obj = raw_claim.get('outcome', '')  # review translated note outcome
            if not obj:
                obj = raw_claim.get('object', '')  # primary translated note object
            object_type = raw_claim.get('object_type', 'outcome')

            if not is_in_scope_claim(subject, subject_type, obj):
                warnings.append(
                    f"Skipped claim for PMID {pmid}: out-of-scope claim "
                    f"'{subject}' -> '{obj}'"
                )
                continue

            if subject_type == 'food':
                subject_validation = self.validator.validate_food_name(subject)
                if not subject_validation.is_valid:
                    warnings.append(
                        f"Skipped claim for PMID {pmid}: suspicious food subject '{subject}'"
                    )
                    continue

            if object_type == 'food':
                object_validation = self.validator.validate_food_name(obj)
                if not object_validation.is_valid:
                    warnings.append(
                        f"Skipped claim for PMID {pmid}: suspicious food object '{obj}'"
                    )
                    continue

            # translated note
            subject_canonical = self._get_canonical_name(subject, subject_type, entity_map)
            object_canonical = self._get_canonical_name(obj, object_type, entity_map)

            # translated note claim translated note
            effect_direction = normalize_effect_direction(raw_claim.get('effect_direction'))
            health_interpretation = normalize_health_interpretation(
                raw_claim.get('health_interpretation')
            )
            if effect_direction == "no_significant_effect":
                health_interpretation = "neutral"
            if health_interpretation == "unclear":
                health_interpretation = infer_health_interpretation(
                    effect_direction,
                    object_canonical,
                )
            direction = normalize_legacy_direction(
                raw_claim.get('direction'),
                effect_direction=effect_direction,
                health_interpretation=health_interpretation,
                outcome_name=object_canonical,
            )
            evidence_snippet = raw_claim.get('evidence_snippet') or raw_claim.get('key_finding', '')
            if not direction:
                warnings.append(
                    f"Skipped claim for PMID {pmid}: missing legacy direction for "
                    f"'{subject_canonical}' -> '{object_canonical}'"
                )
                continue
            if (
                effect_direction == "unclear"
                and health_interpretation == "unclear"
                and looks_like_non_result_snippet(evidence_snippet)
            ):
                warnings.append(
                    f"Skipped claim for PMID {pmid}: non-result evidence snippet for "
                    f"'{subject_canonical}' -> '{object_canonical}'"
                )
                continue
            claim_data = {
                "subject": subject_canonical,
                "subject_type": subject_type,
                "object": object_canonical,
                "object_type": object_type,
                "direction": direction,
                "effect_direction": effect_direction,
                "health_interpretation": health_interpretation,
                "effect_size": raw_claim.get('effect_size'),
                "p_value": raw_claim.get('p_value'),
                "confidence_interval": raw_claim.get('confidence_interval'),
                "key_finding": raw_claim.get('key_finding', ''),
                "evidence_snippet": evidence_snippet,
                "dose": raw_claim.get('dose'),
                "duration": raw_claim.get('duration'),
                "pmid": pmid,
                "study_type": study_type,
                "confidence": raw_claim.get('evidence_strength', 'medium'),
                "population": raw_claim.get('population', ''),
                "original_key": f"{pmid}_{hash(str(raw_claim)) % 10000}"
            }

            # translated note
            claim_id, is_new = self.claim_merger.try_merge_claim(claim_data)

            # translated note ExtractedClaim translated note
            processed.append(ExtractedClaim(
                subject_type=subject_type,
                subject_name=subject_canonical,
                object_type=object_type,
                object_name=object_canonical,
                direction=claim_data['direction'],
                effect_direction=claim_data.get('effect_direction', 'unclear'),
                health_interpretation=claim_data.get('health_interpretation', 'unclear'),
                effect_size=claim_data.get('effect_size'),
                p_value=claim_data.get('p_value'),
                evidence_snippet=claim_data.get('evidence_snippet', ''),
                dose_info={
                    'value': claim_data.get('dose'),
                    'duration': claim_data.get('duration')
                } if claim_data.get('dose') else None,
                pmid=pmid,
                study_type=study_type,
                confidence=claim_data.get('confidence', 'medium')
            ))

        return processed, warnings

    def _get_canonical_name(self, name: str, entity_type: str,
                           entity_map: Dict[str, ExtractedEntity]) -> str:
        """translated note"""
        # translated note
        for entity_name, entity in entity_map.items():
            if name.lower() in [entity_name.lower()] + [a.lower() for a in entity.aliases]:
                return entity_name

        # translated note:translated note,translated note retry claims translated note subject translated note
        # entities translated note canonical node.
        if entity_type in {"food", "strain", "outcome"}:
            canonical, _ = self.entity_normalizer.normalize_entity(name, entity_type)
            if canonical:
                return canonical

        # translated note:translated note
        return name.lower().replace(' ', '_')

    def get_merged_claims(self) -> List[Dict]:
        """translated note claims"""
        return self.claim_merger.get_all_claims()


def _resolve_article_for_extraction(
    selected_article: Dict[str, Any],
    all_articles: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Resolve article text from metadata, falling back to the selected corpus row."""
    pmid = str(selected_article.get("pmid", "")).strip()
    if not pmid:
        return {}

    metadata_article = all_articles.get(pmid)
    if metadata_article:
        merged = {**selected_article, **metadata_article, "pmid": pmid}
        metadata_abstract = str(metadata_article.get("abstract") or "").strip()
        selected_abstract = str(selected_article.get("abstract") or "").strip()
        if selected_abstract and (
            not metadata_abstract
            or len(selected_abstract) > len(metadata_abstract) * 1.25
        ):
            merged["abstract"] = selected_article.get("abstract", "")

        metadata_title = str(metadata_article.get("title") or "").strip()
        selected_title = str(selected_article.get("title") or "").strip()
        if selected_title and (
            not metadata_title
            or len(selected_title) > len(metadata_title) * 1.25
        ):
            merged["title"] = selected_article.get("title", "")
        return merged

    if selected_article.get("abstract"):
        return {
            **selected_article,
            "pmid": pmid,
            "title": selected_article.get("title", ""),
            "abstract": selected_article.get("abstract", ""),
        }

    return {}


def extract_dataset_v3(selected_articles_path: str, output_path: str,
                       max_articles: int = None,
                       checkpoint_interval: int = 25,
                       checkpoint_entity_threshold: int = 80,
                       checkpoint_warning_threshold: int = 3,
                       enable_batch_review_refine: bool = False,
                       baseline_output_path: Optional[str] = None,
                       resume_from_checkpoint: Optional[str] = None) -> Tuple[int, int]:
    """
    translated note(V3)

    Returns:
        (success_count, error_count)
    """
    # translated note
    with open(selected_articles_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    articles = data.get('articles', [])

    if max_articles:
        articles = articles[:max_articles]

    print(f" V3 translated note {len(articles)} translated note")
    print("=" * 60)

    # translated note
    metadata_path = Path(selected_articles_path).parent / '..' / 'metadata' / 'all_articles.json'
    if not metadata_path.exists():
        metadata_path = Path('data/metadata/all_articles.json')

    with open(metadata_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    all_articles = {
        str(a.get('pmid', '')).strip(): a
        for a in all_data.get('articles', [])
        if str(a.get('pmid', '')).strip()
    }

    # translated note
    extractor = EnhancedExtractorV3()

    success_count = 0
    error_count = 0
    all_results = []
    checkpoint_history = []
    processed_since_checkpoint = 0
    new_entities_since_checkpoint = 0
    warnings_since_checkpoint = 0
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    start_index = 0

    if resume_from_checkpoint:
        resume_checkpoint_path = Path(resume_from_checkpoint)
        resume_payload = json.loads(resume_checkpoint_path.read_text(encoding="utf-8"))
        start_index = int(resume_payload.get("total", 0))
        success_count = int(resume_payload.get("success", 0))
        error_count = int(resume_payload.get("error", 0))
        all_results = list(resume_payload.get("results", []))
        checkpoint_history = _load_existing_checkpoint_history(checkpoint_dir)

        resume_pkl_path = resume_checkpoint_path.with_suffix(".pkl")
        with open(resume_pkl_path, "rb") as f:
            resume_graph = pickle.load(f)
        _hydrate_extractor_from_graph(extractor, resume_graph)
        print(f"↪ Resume from checkpoint: {resume_checkpoint_path.name} (processed={start_index})")

    for i, article_info in enumerate(articles[start_index:], start=start_index + 1):
        pmid = str(article_info['pmid']).strip()
        study_type = article_info['study_type']

        print(f"\n[{i}/{len(articles)}] PMID: {pmid}")

        full_article = _resolve_article_for_extraction(article_info, all_articles)
        if not full_article:
            print(f"    translated note")
            error_count += 1
            continue

        registered_before = extractor.entity_normalizer.total_registered_entities()
        result = extractor.extract(full_article, study_type)
        registered_after = extractor.entity_normalizer.total_registered_entities()

        if result.success:
            success_count += 1
            processed_since_checkpoint += 1
            new_entities_since_checkpoint += max(0, registered_after - registered_before)
            warnings_since_checkpoint += len(result.warnings)
            entity_counts = {
                'foods': len([e for e in result.entities if e.entity_type == 'food']),
                'strains': len([e for e in result.entities if e.entity_type == 'strain']),
                'outcomes': len([e for e in result.entities if e.entity_type == 'outcome'])
            }
            print(f"    translated note: {entity_counts['foods']}F/{entity_counts['strains']}S/{entity_counts['outcomes']}O, {len(result.claims)}claims")

            all_results.append({
                'pmid': pmid,
                'title': result.title,
                'success': True,
                'warnings': result.warnings,
                'entities': [{'name': e.name, 'type': e.entity_type} for e in result.entities],
                'claims': [
                    {
                        'subject': c.subject_name,
                        'object': c.object_name,
                        'direction': c.direction,
                        'effect_direction': c.effect_direction,
                        'health_interpretation': c.health_interpretation,
                    }
                    for c in result.claims
                ]
            })
        else:
            error_count += 1
            processed_since_checkpoint += 1
            print(f"    translated note: {result.errors}")
            all_results.append({
                'pmid': pmid,
                'title': result.title,
                'success': False,
                'errors': result.errors
            })

        should_checkpoint = (
            processed_since_checkpoint >= checkpoint_interval
            or new_entities_since_checkpoint >= checkpoint_entity_threshold
            or warnings_since_checkpoint >= checkpoint_warning_threshold
            or i == len(articles)
        )
        if should_checkpoint:
            checkpoint_summary = _run_extraction_checkpoint(
                extractor=extractor,
                all_results=all_results,
                total_articles=i,
                success_count=success_count,
                error_count=error_count,
                checkpoint_dir=checkpoint_dir,
                checkpoint_index=len(checkpoint_history) + 1,
                enable_batch_review_refine=enable_batch_review_refine,
                baseline_output_path=baseline_output_path,
            )
            checkpoint_history.append(checkpoint_summary)
            processed_since_checkpoint = 0
            new_entities_since_checkpoint = 0
            warnings_since_checkpoint = 0

    # translated note claims
    merged_claims = extractor.get_merged_claims()

    extraction_payload = {
        'total': len(articles),
        'success': success_count,
        'error': error_count,
        'merged_claims_count': len(merged_claims),
        'checkpoint_history': checkpoint_history,
        'results': all_results,
        'merged_claims': merged_claims
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(extraction_payload, f, indent=2, ensure_ascii=False)

    # translated note NetworkX translated note
    G = build_networkx_from_v3(merged_claims)

    # translated note NetworkX translated note
    output_stem = Path(output_path).stem  # extraction_v3
    nx_pkl_path = output_dir / f"{output_stem}.pkl"
    nx_json_path = output_dir / f"{output_stem}_networkx.json"

    with open(nx_pkl_path, 'wb') as f:
        pickle.dump(G, f)

    with open(nx_json_path, 'w', encoding='utf-8') as f:
        json.dump(nx.node_link_data(G), f, indent=2, ensure_ascii=False)

    quality_report = summarize_extraction_quality(extraction_payload)
    quality_report_path = output_dir / f"{output_stem}_quality_report.json"
    with open(quality_report_path, 'w', encoding='utf-8') as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 60)
    print(f" V3 translated note")
    print(f"   translated note: {len(articles)}")
    print(f"   translated note: {success_count}")
    print(f"   translated note: {error_count}")
    print(f"   translated note Claims: {len(merged_claims)}")
    print(f"   translated note: {G.number_of_nodes()}")
    print(f"   translated note: {G.number_of_edges()}")
    print(f"   JSONtranslated note: {output_path}")
    print(f"   NetworkXtranslated note: {nx_pkl_path}")
    print(f"   NetworkX JSON: {nx_json_path}")
    print(f"   translated note: {quality_report_path}")

    return success_count, error_count


def _load_existing_checkpoint_history(checkpoint_dir: Path) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for checkpoint_json in sorted(checkpoint_dir.glob("checkpoint_*articles.json")):
        payload = json.loads(checkpoint_json.read_text(encoding="utf-8"))
        stem = checkpoint_json.with_suffix("")
        summary = {
            "checkpoint_index": len(history) + 1,
            "articles_processed": payload.get("total", 0),
            "merged_claims": payload.get("merged_claims_count", len(payload.get("merged_claims", []))),
            "quality_report_path": str(Path(f"{stem}_quality_report.json")),
            "json_path": str(checkpoint_json),
            "pkl_path": str(checkpoint_json.with_suffix(".pkl")),
            "review_refine_ran": False,
        }
        delta_path = Path(f"{stem}_delta_review.json")
        if delta_path.exists():
            summary["delta_review_path"] = str(delta_path)

        review_path = Path(f"{stem}_reviewer_result.json")
        candidate_path = Path(f"{stem}_refine_candidates.json")
        refiner_path = Path(f"{stem}_refiner_result.json")
        if review_path.exists() or candidate_path.exists() or refiner_path.exists():
            summary["review_refine_ran"] = True
            rr = {}
            if review_path.exists():
                rr["review_path"] = str(review_path)
            if candidate_path.exists():
                rr["candidate_path"] = str(candidate_path)
                rr["candidate_count"] = len(json.loads(candidate_path.read_text(encoding="utf-8")))
            if refiner_path.exists():
                rr["refine_path"] = str(refiner_path)
            summary["review_refine_result"] = rr
        history.append(summary)
    return history


def _run_extraction_checkpoint(
    *,
    extractor: "EnhancedExtractorV3",
    all_results: List[Dict[str, Any]],
    total_articles: int,
    success_count: int,
    error_count: int,
    checkpoint_dir: Path,
    checkpoint_index: int,
    enable_batch_review_refine: bool,
    baseline_output_path: Optional[str],
) -> Dict[str, Any]:
    merged_claims = extractor.get_merged_claims()
    payload = {
        "total": total_articles,
        "success": success_count,
        "error": error_count,
        "merged_claims_count": len(merged_claims),
        "results": list(all_results),
        "merged_claims": merged_claims,
    }
    stem = checkpoint_dir / f"checkpoint_{checkpoint_index:03d}_{total_articles:03d}articles"
    json_path = Path(f"{stem}.json")
    pkl_path = Path(f"{stem}.pkl")
    nx_json_path = Path(f"{stem}_networkx.json")
    quality_path = Path(f"{stem}_quality_report.json")

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    graph = build_networkx_from_v3(merged_claims)
    with open(pkl_path, "wb") as f:
        pickle.dump(graph, f)
    nx_json_path.write_text(json.dumps(nx.node_link_data(graph), indent=2, ensure_ascii=False), encoding="utf-8")

    quality_report = summarize_extraction_quality(payload)
    quality_path.write_text(json.dumps(quality_report, indent=2, ensure_ascii=False), encoding="utf-8")

    checkpoint_summary = {
        "checkpoint_index": checkpoint_index,
        "articles_processed": total_articles,
        "merged_claims": len(merged_claims),
        "quality_report_path": str(quality_path),
        "json_path": str(json_path),
        "pkl_path": str(pkl_path),
        "review_refine_ran": False,
    }

    if baseline_output_path:
        try:
            from batch_review import compare_extraction_batches  # type: ignore
        except ImportError:
            from .batch_review import compare_extraction_batches  # type: ignore
        baseline_payload = json.loads(Path(baseline_output_path).read_text(encoding="utf-8"))
        delta_report = compare_extraction_batches(payload, baseline_payload)
        delta_path = Path(f"{stem}_delta_review.json")
        delta_path.write_text(json.dumps(delta_report, indent=2, ensure_ascii=False), encoding="utf-8")
        checkpoint_summary["delta_review_path"] = str(delta_path)

    should_review = quality_report.get("review_recommendation", {}).get("should_run_batch_review", False)
    if enable_batch_review_refine and should_review:
        review_refine_result = _run_checkpoint_review_refine(
            extractor=extractor,
            review_target_pkl=pkl_path,
            review_target_json=nx_json_path,
            checkpoint_stem=str(stem),
        )
        checkpoint_summary["review_refine_ran"] = True
        checkpoint_summary["review_refine_result"] = review_refine_result

    return checkpoint_summary


def _run_checkpoint_review_refine(
    *,
    extractor: "EnhancedExtractorV3",
    review_target_pkl: Path,
    review_target_json: Path,
    checkpoint_stem: str,
) -> Dict[str, Any]:
    import asyncio
    import sys

    project_root = Path(__file__).resolve().parents[1]
    agents_dir = project_root / "agents"
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(agents_dir) not in sys.path:
        sys.path.insert(0, str(agents_dir))

    previous_pickle = os.environ.get("FOOD_AI_REFINER_KG_PATH")
    previous_json = os.environ.get("FOOD_AI_KG_JSON_PATH")
    previous_pickle_alias = os.environ.get("FOOD_AI_KG_PICKLE_PATH")
    previous_quality = os.environ.get("FOOD_AI_QUALITY_REPORT_PATH")

    os.environ["FOOD_AI_REFINER_KG_PATH"] = str(review_target_pkl)
    os.environ["FOOD_AI_KG_PICKLE_PATH"] = str(review_target_pkl)
    os.environ["FOOD_AI_KG_JSON_PATH"] = str(review_target_json)
    quality_report_path = Path(f"{checkpoint_stem}_quality_report.json")
    if quality_report_path.exists():
        os.environ["FOOD_AI_QUALITY_REPORT_PATH"] = str(quality_report_path)

    try:
        from kg_reviewer_agent import review_graph_async
        from kg_refiner_agent import refine_graph_from_candidates_async
        from food_ai.refine_candidates import extract_refine_candidates_from_review, select_refine_candidates

        review_result = asyncio.run(review_graph_async())
        review_raw = review_result.get("agent_response", "")
        candidates = select_refine_candidates(extract_refine_candidates_from_review(review_raw), limit=5)

        refine_result = None
        if candidates:
            refine_result = asyncio.run(
                refine_graph_from_candidates_async(review_raw=review_raw, candidates=candidates)
            )
            refined_graph = pickle.load(open(review_target_pkl, "rb"))
            _hydrate_extractor_from_graph(extractor, refined_graph)

        review_path = Path(f"{checkpoint_stem}_reviewer_result.json")
        review_path.write_text(json.dumps(review_result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        candidate_path = Path(f"{checkpoint_stem}_refine_candidates.json")
        candidate_path.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
        result = {
            "review_path": str(review_path),
            "candidate_path": str(candidate_path),
            "candidate_count": len(candidates),
        }
        if refine_result is not None:
            refine_path = Path(f"{checkpoint_stem}_refiner_result.json")
            refine_path.write_text(json.dumps(refine_result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            result["refine_path"] = str(refine_path)
        return result
    finally:
        if previous_pickle is None:
            os.environ.pop("FOOD_AI_REFINER_KG_PATH", None)
        else:
            os.environ["FOOD_AI_REFINER_KG_PATH"] = previous_pickle
        if previous_pickle_alias is None:
            os.environ.pop("FOOD_AI_KG_PICKLE_PATH", None)
        else:
            os.environ["FOOD_AI_KG_PICKLE_PATH"] = previous_pickle_alias
        if previous_json is None:
            os.environ.pop("FOOD_AI_KG_JSON_PATH", None)
        else:
            os.environ["FOOD_AI_KG_JSON_PATH"] = previous_json
        if previous_quality is None:
            os.environ.pop("FOOD_AI_QUALITY_REPORT_PATH", None)
        else:
            os.environ["FOOD_AI_QUALITY_REPORT_PATH"] = previous_quality


def _hydrate_extractor_from_graph(extractor: "EnhancedExtractorV3", graph: nx.DiGraph) -> None:
    extractor.claim_merger.claims_index = {}
    extractor.entity_normalizer.entity_index = {}
    extractor.entity_normalizer.entity_embeddings = defaultdict(dict)

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("node_type")
        if node_type == "claim":
            claim_data = dict(data)
            claim_data.setdefault("evidence_list", [])
            claim_data.setdefault("merged_from", [])
            claim_data.setdefault("first_seen", "")
            claim_data.setdefault("last_updated", "")
            claim_data["evidence_count"] = len(claim_data.get("evidence_list", []))
            extractor.claim_merger.claims_index[node_id] = claim_data
        elif node_type in {"food", "strain", "outcome"}:
            extractor.entity_normalizer._register_entity(
                data.get("name", ""),
                node_type,
                [data.get("name", "")],
            )


def build_networkx_from_v3(merged_claims: List[Dict]) -> nx.DiGraph:
    """
    translated note V3 merged_claims translated note NetworkX translated note

    V3 translated note:
    - Claim translated note,translated note evidence_list translated note
    - Entity translated note: food, strain, outcome
    - translated note: entity -> claim (subject), claim -> entity (object)
    """
    G = nx.DiGraph()

    # translated note
    entity_nodes = set()
    claim_nodes = set()

    for claim in merged_claims:
        claim_id = claim['claim_id']
        subject_name = claim['subject_name']
        object_name = claim['object_name']
        subject_type = claim['subject_type']
        object_type = claim['object_type']

        # 1. translated note Claim translated note(translated note)
        if claim_id not in claim_nodes:
            claim_attrs = {
                'node_type': 'claim',
                'claim_id': claim_id,
                'claim_text': claim.get('claim_text', ''),
                'subject_name': subject_name,
                'object_name': object_name,
                'subject_type': subject_type,
                'object_type': object_type,
                'direction': claim.get('direction', ''),
                'effect_direction': claim.get('effect_direction', 'unclear'),
                'health_interpretation': claim.get('health_interpretation', 'unclear'),
                'evidence_list': claim.get('evidence_list', []),
                'evidence_count': claim.get('evidence_count', 0),
                'confidence_score': claim.get('confidence_score', 0.0),
                'dose_info': claim.get('dose_info'),
                # Preserve refiner-set quality annotations across rebuild.
                'quality_flags': list(claim.get('quality_flags', []) or []),
            }
            G.add_node(claim_id, **claim_attrs)
            claim_nodes.add(claim_id)

        # 2. translated note Subject Entity translated note
        subject_node_id = f"{subject_type}_{subject_name}"
        if subject_node_id not in entity_nodes:
            G.add_node(
                subject_node_id,
                node_type=subject_type,
                name=subject_name,
                entity_type=subject_type
            )
            entity_nodes.add(subject_node_id)

        # 3. translated note Object Entity translated note
        object_node_id = f"{object_type}_{object_name}"
        if object_node_id not in entity_nodes:
            G.add_node(
                object_node_id,
                node_type=object_type,
                name=object_name,
                entity_type=object_type
            )
            entity_nodes.add(object_node_id)

        # 4. translated note: subject -> claim
        G.add_edge(
            subject_node_id,
            claim_id,
            edge_type='subject_of',
            relation='has_effect'
        )

        # 5. translated note: claim -> object
        G.add_edge(
            claim_id,
            object_node_id,
            edge_type='object_of',
            relation='affects'
        )

    print(f"\n🔨 NetworkX translated note:")
    print(f"   translated note: {len(entity_nodes)}")
    print(f"   Claimtranslated note: {len(claim_nodes)}")
    print(f"   translated note: {G.number_of_nodes()}")
    print(f"   translated note: {G.number_of_edges()}")

    # Re-stamp entity-level quality_status from claim quality_flags so refiner-applied
    # `mark_out_of_scope` survives the rebuild from merged_claims.
    for claim_id in claim_nodes:
        for flag in G.nodes[claim_id].get("quality_flags", []) or []:
            if not isinstance(flag, str) or not flag.startswith("entity_out_of_scope:"):
                continue
            parts = flag.split(":", 2)
            if len(parts) < 3:
                continue
            ent_type, ent_name = parts[1], parts[2]
            ent_node_id = f"{ent_type}_{ent_name}"
            if ent_node_id in G.nodes:
                G.nodes[ent_node_id]["quality_status"] = "out_of_scope"
                G.nodes[ent_node_id].setdefault("out_of_scope_reason", "carried_via_claim_flag")

    return G


if __name__ == "__main__":
    import sys

    test_mode = '--test' in sys.argv
    max_articles = 5 if test_mode else None

    if test_mode:
        print("🧪 translated note: translated note5translated note")

    extract_dataset_v3(
        selected_articles_path='data/processed/selected_50_high_quality.json',
        output_path='data/processed/extraction_v3_test.json' if test_mode else 'data/processed/extraction_v3.json',
        max_articles=max_articles
    )
