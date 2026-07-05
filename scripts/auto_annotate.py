#!/usr/bin/env python3
"""
translated note - translated note LLM translated note
translated note, translated note, translated note

translated note:
    # translated note
    python scripts/auto_annotate.py --input data/metadata/relevant_articles.json --task entity --output data/annotations/entities.json
    
    # translated note
    python scripts/auto_annotate.py --input data/metadata/relevant_articles.json --task relation --output data/annotations/relations.json
    
    # translated note
    python scripts/auto_annotate.py --input data/metadata/relevant_articles.json --task custom --prompt-file prompts/my_task.txt --output data/annotations/custom.json
    
    # translated note
    python scripts/auto_annotate.py --input data/metadata/relevant_articles.json --task entity --format train --output data/annotations/train_data.jsonl
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# translated note
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pydantic import BaseModel, Field, RootModel
    from pydantic_ai import Agent
except ImportError:
    print("translated note: pip install pydantic-ai")
    sys.exit(1)

from food_ai.pydantic_ai_client import create_poe_model


# ==================== translated note ====================

class AnnotationTask(Enum):
    """translated note"""
    ENTITY = "entity"           # translated note
    RELATION = "relation"       # translated note
    CLASSIFICATION = "classification"  # translated note
    SUMMARY = "summary"         # translated note
    CUSTOM = "custom"           # translated note


class EntityItem(BaseModel):
    text: str
    type: Literal["FOOD", "BACTERIA", "HEALTH_CONDITION", "BIOACTIVE_COMPOUND", "BODY_PART", "MECHANISM"]
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class EntityAnnotation(BaseModel):
    entities: List[EntityItem] = Field(default_factory=list)


class RelationItem(BaseModel):
    subject: str
    predicate: Literal["TREATS", "CONTAINS", "PRODUCES", "AFFECTS", "PREVENTS", "MODULATES"]
    object: str
    evidence: str


class RelationAnnotation(BaseModel):
    relations: List[RelationItem] = Field(default_factory=list)


class ClassificationAnnotation(BaseModel):
    study_type: Literal["RCT", "review", "meta_analysis", "observational", "in_vitro", "animal", "other"]
    food_category: Literal["dairy", "fermented_vegetable", "fermented_beverage", "probiotic_supplement", "other"]
    health_domain: Literal["gastrointestinal", "immune", "metabolic", "mental", "cardiovascular", "other"]
    evidence_level: Literal["high", "moderate", "low", "very_low"]
    keywords: List[str] = Field(default_factory=list)
    reasoning: str


class SummaryAnnotation(BaseModel):
    research_question: str
    methods: str
    key_findings: str
    conclusion: str
    limitations: str = "translated note"
    clinical_significance: str = "translated note"


class CustomAnnotation(RootModel[Dict[str, Any]]):
    pass


def output_type_for_task(task: AnnotationTask) -> type[BaseModel]:
    if task == AnnotationTask.ENTITY:
        return EntityAnnotation
    if task == AnnotationTask.RELATION:
        return RelationAnnotation
    if task == AnnotationTask.CLASSIFICATION:
        return ClassificationAnnotation
    if task == AnnotationTask.SUMMARY:
        return SummaryAnnotation
    return CustomAnnotation


# translated note
ENTITY_SYSTEM_PROMPT = """translated note.translated note:

translated note:
1. FOOD - translated note/translated note(translated note:yogurt, kimchi, kefir, sauerkraut, miso, natto, kombucha)
2. BACTERIA - translated note/translated note(translated note:Lactobacillus, Bifidobacterium, Streptococcus)
3. HEALTH_CONDITION - translated note/translated note(translated note:diabetes, obesity, IBS, inflammation, diarrhea)
4. BIOACTIVE_COMPOUND - translated note(translated note:protein, peptide, SCFA, butyrate, propionate)
5. BODY_PART - translated note/translated note(translated note:gut, intestine, colon, immune system, brain)
6. MECHANISM - translated note/translated note(translated note:fermentation, colonization, adhesion, antimicrobial)

translated note(JSON):
{
  "entities": [
    {"text": "translated note", "type": "translated note", "start": translated note, "end": translated note}
  ]
}

translated note:
- translated note JSON,translated note
- translated note,translated note
- translated note"""

ENTITY_USER_TEMPLATE = """translated note:

translated note:{title}

translated note:{abstract}

translated note JSON translated note."""


# translated note
RELATION_SYSTEM_PROMPT = """translated note.translated note.

translated note:
1. TREATS - translated note/translated note(translated note/translated note)
2. CONTAINS - translated note(translated note/translated note)
3. PRODUCES - translated note(translated note)
4. AFFECTS - translated note(translated note/translated note)
5. PREVENTS - translated note(translated note)
6. MODULATES - translated note(translated note)

translated note(JSON):
{
  "relations": [
    {"subject": "translated note", "predicate": "translated note", "object": "translated note", "evidence": "translated note"}
  ]
}

translated note:
- translated note JSON,translated note
- translated note,translated note
- evidence translated note"""

RELATION_USER_TEMPLATE = """translated note:

translated note:{title}

translated note:{abstract}

translated note JSON translated note."""


# translated note
CLASSIFICATION_SYSTEM_PROMPT = """translated note.translated note.

translated note:
1. study_type - translated note:RCT(translated note), review(translated note), meta_analysis(translated note), observational(translated note), in_vitro(translated note), animal(translated note)
2. food_category - translated note:dairy(translated note), fermented_vegetable(translated note), fermented_beverage(translated note), probiotic_supplement(translated note), other(translated note)
3. health_domain - translated note:gastrointestinal(translated note), immune(translated note), metabolic(translated note), mental(translated note/translated note), cardiovascular(translated note), other(translated note)
4. evidence_level - translated note:high(translated note), moderate(translated note), low(translated note), very_low(translated note)

translated note(JSON):
{
  "study_type": "translated note",
  "food_category": "translated note",
  "health_domain": "translated note",
  "evidence_level": "translated note",
  "keywords": ["translated note1", "translated note2"],
  "reasoning": "translated note(translated note)"
}

translated note:translated note JSON,translated note."""

CLASSIFICATION_USER_TEMPLATE = """translated note:

translated note:{title}

translated note:{abstract}

translated note:{journal}
translated note:{year}

translated note JSON translated note."""


# translated note
SUMMARY_SYSTEM_PROMPT = """translated note.translated note.

translated note(JSON):
{
  "research_question": "translated note/translated note",
  "methods": "translated note(translated note)",
  "key_findings": "translated note",
  "conclusion": "translated note",
  "limitations": "translated note(translated note)",
  "clinical_significance": "translated note(translated note)"
}

translated note:
- translated note1-2translated note
- translated note JSON,translated note
- translated note,translated note "translated note"
"""

SUMMARY_USER_TEMPLATE = """translated note:

translated note:{title}

translated note:{abstract}

translated note JSON translated note."""


@dataclass
class AnnotationResult:
    """translated note"""
    pmid: str
    title: str
    task: str
    annotation: Dict[str, Any]
    confidence: Optional[float] = None
    model: str = ""
    annotated_at: str = ""
    
    def __post_init__(self):
        if not self.annotated_at:
            self.annotated_at = datetime.now().isoformat()


def get_annotation_agent(task: AnnotationTask, system_prompt: str, model: str = "minimax-m2.7") -> Agent:
    """translated note pydantic-ai translated note Agent."""
    return Agent(
        create_poe_model(model),
        output_type=output_type_for_task(task),
        system_prompt=system_prompt,
        retries=2,
    )


def get_task_prompts(task: AnnotationTask, custom_prompt_file: Optional[Path] = None) -> tuple:
    """translated note"""
    if task == AnnotationTask.ENTITY:
        return ENTITY_SYSTEM_PROMPT, ENTITY_USER_TEMPLATE
    elif task == AnnotationTask.RELATION:
        return RELATION_SYSTEM_PROMPT, RELATION_USER_TEMPLATE
    elif task == AnnotationTask.CLASSIFICATION:
        return CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_TEMPLATE
    elif task == AnnotationTask.SUMMARY:
        return SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_TEMPLATE
    elif task == AnnotationTask.CUSTOM:
        if not custom_prompt_file or not custom_prompt_file.exists():
            raise ValueError("translated note --prompt-file translated note")
        with open(custom_prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        # translated note system prompt translated note user template,translated note --- translated note
        if "---" in content:
            parts = content.split("---", 1)
            return parts[0].strip(), parts[1].strip()
        return content, "{title}\n\n{abstract}"
    else:
        raise ValueError(f"translated note: {task}")


def annotate_article(
    article: Dict,
    agent: Agent,
    task: AnnotationTask,
    user_template: str,
    model: str = "minimax-m2.7",
    temperature: float = 0.1,
    max_retries: int = 3
) -> Optional[AnnotationResult]:
    """
    translated note
    
    Args:
        article: translated note
        agent: pydantic-ai translated note Agent
        task: translated note
        user_template: translated note
        model: translated note
        temperature: translated note
        max_retries: translated note
        
    Returns:
        AnnotationResult translated note None
    """
    pmid = article.get("pmid", "")
    title = article.get("title", "")
    abstract = article.get("abstract", "")
    journal = article.get("journal", "")
    year = article.get("year", "")
    
    if not title:
        return None
    
    # translated note
    user_prompt = user_template.format(
        title=title,
        abstract=abstract[:3000] if abstract else "translated note",
        journal=journal,
        year=year
    )
    
    for attempt in range(max_retries):
        try:
            annotation_output = agent.run_sync(user_prompt, model_settings={"temperature": temperature}).output
            if isinstance(annotation_output, RootModel):
                annotation = annotation_output.root
            else:
                annotation = annotation_output.model_dump()
            
            return AnnotationResult(
                pmid=pmid,
                title=title,
                task=task.value,
                annotation=annotation,
                model=model,
                annotated_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            print(f"  translated note PMID {pmid}: {e}")
            return None


def batch_annotate(
    input_file: Path,
    output_file: Path,
    task: AnnotationTask,
    system_prompt: str,
    user_template: str,
    model: str = "minimax-m2.7",
    temperature: float = 0.1,
    save_interval: int = 10,
    resume: bool = True,
    limit: Optional[int] = None
) -> Dict:
    """
    translated note
    
    Args:
        input_file: translated note
        output_file: translated note
        task: translated note
        system_prompt: translated note
        user_template: translated note
        model: translated note
        temperature: translated note
        save_interval: translated note
        resume: translated note
        limit: translated note(translated note)
        
    Returns:
        translated note
    """
    agent = get_annotation_agent(task, system_prompt=system_prompt, model=model)
    
    # translated note
    print(f"translated note: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    if limit:
        articles = articles[:limit]
    
    total = len(articles)
    print(f"translated note {total} translated note")
    
    # translated note
    processed_pmids = set()
    results = []
    
    if resume and output_file.exists():
        print(f"translated note,translated note: {output_file}")
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            results = existing_data.get("annotations", [])
            processed_pmids = {r["pmid"] for r in results}
        print(f"translated note {len(results)} translated note,translated note {total - len(results)} translated note")
    
    # translated note
    articles_to_process = [a for a in articles if a["pmid"] not in processed_pmids]
    
    # translated note
    success_count = len(results)
    fail_count = 0
    
    print(f"\ntranslated note,translated note: {task.value},translated note: {model}")
    print("-" * 60)
    
    from tqdm import tqdm
    
    with tqdm(total=len(articles_to_process), desc="translated note") as pbar:
        for i, article in enumerate(articles_to_process):
            result = annotate_article(
                article=article,
                agent=agent,
                task=task,
                user_template=user_template,
                model=model,
                temperature=temperature
            )
            
            if result:
                results.append(asdict(result))
                success_count += 1
            else:
                fail_count += 1
            
            pbar.update(1)
            
            # translated note
            if (i + 1) % save_interval == 0:
                save_annotations(output_file, results, task.value, model)
                pbar.set_postfix({"translated note": success_count, "translated note": fail_count})
            
            # translated note
            time.sleep(0.1)
    
    # translated note
    save_annotations(output_file, results, task.value, model)
    
    # translated note
    stats = {
        "total": total,
        "success": success_count,
        "failed": fail_count
    }
    
    print("\n" + "=" * 60)
    print("translated note!")
    print("=" * 60)
    print(f"translated note: {total}")
    print(f"  translated note: {success_count}")
    print(f"  translated note: {fail_count}")
    print(f"\ntranslated note: {output_file}")
    
    return stats


def save_annotations(output_file: Path, results: List[Dict], task: str, model: str):
    """translated note"""
    output_data = {
        "task": task,
        "model": model,
        "generated_at": datetime.now().isoformat(),
        "total": len(results),
        "annotations": results
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


def convert_to_train_format(
    annotation_file: Path,
    original_file: Path,
    output_file: Path,
    task: AnnotationTask
):
    """
    translated note(JSONL)
    
    Args:
        annotation_file: translated note
        original_file: translated note
        output_file: translated note(JSONL translated note)
        task: translated note
    """
    # translated note
    with open(annotation_file, "r", encoding="utf-8") as f:
        anno_data = json.load(f)
    
    with open(original_file, "r", encoding="utf-8") as f:
        orig_data = json.load(f)
    
    # translated note
    article_map = {a["pmid"]: a for a in orig_data.get("articles", [])}
    
    # translated note
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for anno in anno_data.get("annotations", []):
            pmid = anno["pmid"]
            article = article_map.get(pmid, {})
            
            # translated note
            sample = {
                "pmid": pmid,
                "text": f"translated note: {article.get('title', '')}\n\ntranslated note: {article.get('abstract', '')}",
                "annotation": anno.get("annotation", {}),
                "metadata": {
                    "title": article.get("title", ""),
                    "journal": article.get("journal", ""),
                    "year": article.get("year", ""),
                    "task": task.value
                }
            }
            
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    
    print(f"translated note: {output_file}")
    print(f"translated note {len(anno_data.get('annotations', []))} translated note")


def main():
    parser = argparse.ArgumentParser(description="translated note")
    parser.add_argument("--input", type=Path, required=True,
                        help="translated note")
    parser.add_argument("--output", type=Path, required=True,
                        help="translated note")
    parser.add_argument("--task", type=str, required=True,
                        choices=["entity", "relation", "classification", "summary", "custom"],
                        help="translated note")
    parser.add_argument("--prompt-file", type=Path,
                        help="translated note(translated note custom translated note)")
    parser.add_argument("--model", type=str, default="minimax-m2.7",
                        help="translated note")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="translated note")
    parser.add_argument("--save-interval", type=int, default=10,
                        help="translated note")
    parser.add_argument("--no-resume", action="store_true",
                        help="translated note")
    parser.add_argument("--limit", type=int,
                        help="translated note(translated note)")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "train"],
                        help="translated note")
    parser.add_argument("--original-file", type=Path,
                        help="translated note(translated note)")
    
    args = parser.parse_args()
    
    # translated note
    task = AnnotationTask(args.task)
    
    # translated note
    system_prompt, user_template = get_task_prompts(task, args.prompt_file)
    
    # translated note
    stats = batch_annotate(
        input_file=args.input,
        output_file=args.output,
        task=task,
        system_prompt=system_prompt,
        user_template=user_template,
        model=args.model,
        temperature=args.temperature,
        save_interval=args.save_interval,
        resume=not args.no_resume,
        limit=args.limit
    )
    
    # translated note
    if args.format == "train":
        train_output = args.output.with_suffix(".jsonl")
        original_file = args.original_file or args.input
        convert_to_train_format(
            annotation_file=args.output,
            original_file=original_file,
            output_file=train_output,
            task=task
        )


if __name__ == "__main__":
    main()
