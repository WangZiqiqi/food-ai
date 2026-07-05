"""
translated note Schema translated note
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class StudyType(Enum):
    """translated note"""
    RCT = "randomized_controlled_trial"
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    OBSERVATIONAL = "observational_study"
    CASE_CONTROL = "case_control"
    COHORT = "cohort_study"
    REVIEW = "review"
    UNKNOWN = "unknown"


class EffectDirection(Enum):
    """Legacy overall direction retained for backward compatibility."""
    POSITIVE = "positive"      # translated note
    NEGATIVE = "negative"      # translated note
    NEUTRAL = "neutral"        # translated note/translated note
    MIXED = "mixed"            # translated note
    UNKNOWN = "unknown"


class MeasuredEffectDirection(Enum):
    """Measured outcome direction, separated from health interpretation."""
    INCREASED = "increased"
    DECREASED = "decreased"
    CHANGED = "changed"
    NO_SIGNIFICANT_EFFECT = "no_significant_effect"
    ASSOCIATED = "associated"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class HealthInterpretation(Enum):
    """Health/domain interpretation of an effect direction."""
    BENEFICIAL = "beneficial"
    HARMFUL = "harmful"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNCLEAR = "unclear"


@dataclass
class Strain:
    """translated note"""
    name: str                          # translated note,translated note "Lactobacillus acidophilus La5"
    genus: Optional[str] = None        # translated note,translated note "Lactobacillus"
    species: Optional[str] = None      # translated note,translated note "acidophilus"
    strain_id: Optional[str] = None    # translated note,translated note "La5"
    synonyms: List[str] = field(default_factory=list)  # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "genus": self.genus,
            "species": self.species,
            "strain_id": self.strain_id,
            "synonyms": self.synonyms
        }


@dataclass
class FoodProduct:
    """translated note"""
    name: str                          # translated note,translated note "Yogurt"
    category: Optional[str] = None     # translated note,translated note "fermented_milk"
    form: Optional[str] = None         # translated note,translated note "capsule", "liquid", "powder"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "form": self.form
        }


@dataclass
class Population:
    """translated note"""
    name: str                          # translated note,translated note "Type 2 Diabetes"
    condition: Optional[str] = None    # translated note
    age_group: Optional[str] = None    # translated note,translated note "adults", "children"
    ethnicity: Optional[str] = None    # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "age_group": self.age_group,
            "ethnicity": self.ethnicity
        }


@dataclass
class Outcome:
    """translated note"""
    name: str                          # translated note,translated note "Fasting Glucose"
    unit: Optional[str] = None         # translated note,translated note "mg/dL"
    measurement_method: Optional[str] = None  # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "unit": self.unit,
            "measurement_method": self.measurement_method
        }


@dataclass
class Dose:
    """translated note"""
    value: Optional[float] = None      # translated note
    unit: Optional[str] = None         # translated note,translated note "CFU/day", "g/day"
    frequency: Optional[str] = None    # translated note,translated note "once_daily", "twice_daily"
    duration_days: Optional[int] = None  # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "frequency": self.frequency,
            "duration_days": self.duration_days
        }


@dataclass
class Institution:
    """translated note"""
    name: str                          # translated note
    country: Optional[str] = None      # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "country": self.country
        }


@dataclass
class Evidence:
    """translated note(translated note)"""
    pmid: str                          # PubMed ID
    pmcid: Optional[str] = None        # PMC ID
    title: str = ""
    authors: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    study_type: StudyType = StudyType.UNKNOWN
    sample_size: Optional[int] = None  # translated note
    funding_sources: List[str] = field(default_factory=list)  # translated note
    
    def to_dict(self) -> Dict[str, Any]:
        # translated note study_type translated note StudyType translated note
        if isinstance(self.study_type, str):
            study_type_value = self.study_type
        else:
            study_type_value = self.study_type.value
        
        return {
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "study_type": study_type_value,
            "sample_size": self.sample_size,
            "funding_sources": self.funding_sources
        }


@dataclass
class Claim:
    """translated note(translated note)"""
    claim_key: str                     # translated note
    subject_type: str                  # translated note:"strain", "food_product"
    subject_name: str                  # translated note
    predicate: str                     # translated note:"has_effect", "studied_in"
    object_type: str                   # translated note:"outcome", "population"
    object_name: str                   # translated note
    
    # translated note
    direction: EffectDirection = EffectDirection.UNKNOWN
    effect_direction: MeasuredEffectDirection = MeasuredEffectDirection.UNCLEAR
    health_interpretation: HealthInterpretation = HealthInterpretation.UNCLEAR
    effect_size: Optional[str] = None  # translated note,translated note "OR 0.292 (95% CI: 0.148-0.577)"
    p_value: Optional[str] = None      # p translated note
    confidence_level: Optional[str] = None  # translated note
    
    # translated note
    evidence_snippet: str = ""         # translated note
    evidence_ref: Optional[str] = None # translated note PMID
    
    # translated note
    dose: Optional[Dose] = None
    
    def to_dict(self) -> Dict[str, Any]:
        # translated note direction translated note EffectDirection translated note
        direction_value = self.direction if isinstance(self.direction, str) else self.direction.value
        effect_direction_value = (
            self.effect_direction
            if isinstance(self.effect_direction, str)
            else self.effect_direction.value
        )
        health_interpretation_value = (
            self.health_interpretation
            if isinstance(self.health_interpretation, str)
            else self.health_interpretation.value
        )
        
        return {
            "claim_key": self.claim_key,
            "subject_type": self.subject_type,
            "subject_name": self.subject_name,
            "predicate": self.predicate,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "direction": direction_value,
            "effect_direction": effect_direction_value,
            "health_interpretation": health_interpretation_value,
            "effect_size": self.effect_size,
            "p_value": self.p_value,
            "confidence_level": self.confidence_level,
            "evidence_snippet": self.evidence_snippet,
            "evidence_ref": self.evidence_ref,
            "dose": self.dose.to_dict() if self.dose else None
        }


@dataclass
class KnowledgeGraph:
    """translated note"""
    strains: Dict[str, Strain] = field(default_factory=dict)
    food_products: Dict[str, FoodProduct] = field(default_factory=dict)
    populations: Dict[str, Population] = field(default_factory=dict)
    outcomes: Dict[str, Outcome] = field(default_factory=dict)
    institutions: Dict[str, Institution] = field(default_factory=dict)
    evidences: Dict[str, Evidence] = field(default_factory=dict)
    claims: Dict[str, Claim] = field(default_factory=dict)
    
    def add_strain(self, strain: Strain):
        self.strains[strain.name] = strain
    
    def add_food_product(self, food: FoodProduct):
        self.food_products[food.name] = food
    
    def add_population(self, pop: Population):
        self.populations[pop.name] = pop
    
    def add_outcome(self, outcome: Outcome):
        self.outcomes[outcome.name] = outcome
    
    def add_institution(self, inst: Institution):
        self.institutions[inst.name] = inst
    
    def add_evidence(self, evidence: Evidence):
        self.evidences[evidence.pmid] = evidence
    
    def add_claim(self, claim: Claim):
        self.claims[claim.claim_key] = claim
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strains": {k: v.to_dict() for k, v in self.strains.items()},
            "food_products": {k: v.to_dict() for k, v in self.food_products.items()},
            "populations": {k: v.to_dict() for k, v in self.populations.items()},
            "outcomes": {k: v.to_dict() for k, v in self.outcomes.items()},
            "institutions": {k: v.to_dict() for k, v in self.institutions.items()},
            "evidences": {k: v.to_dict() for k, v in self.evidences.items()},
            "claims": {k: v.to_dict() for k, v in self.claims.items()},
        }
    
    def to_networkx(self):
        """translated note NetworkX translated note"""
        import networkx as nx
        
        G = nx.DiGraph()
        
        # translated note
        for name, strain in self.strains.items():
            G.add_node(name, type="strain", **strain.to_dict())
        
        for name, food in self.food_products.items():
            G.add_node(name, type="food_product", **food.to_dict())
        
        for name, pop in self.populations.items():
            G.add_node(name, type="population", **pop.to_dict())
        
        for name, outcome in self.outcomes.items():
            G.add_node(name, type="outcome", **outcome.to_dict())
        
        # translated note(claims)
        for claim in self.claims.values():
            subject = claim.subject_name
            obj = claim.object_name
            if subject in G.nodes and obj in G.nodes:
                G.add_edge(
                    subject, obj,
                    predicate=claim.predicate,
                    direction=claim.direction.value,
                    effect_size=claim.effect_size,
                    evidence=claim.evidence_snippet
                )
        
        return G
