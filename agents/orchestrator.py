#!/usr/bin/env python3
"""
KG Refinement Orchestrator V3 - translated note

translated note:
- Reviewer Agent: Claude Agent SDK (translated note) -> translated note
- DecisionAgent: pydantic-ai Agent (translated note) -> translated note
- Refiner Agent: Claude Agent SDK (translated note) -> translated note

Refiner translated note,translated note review
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from food_ai.refine_candidates import (
    extract_refine_candidates_from_review,
    select_refine_candidates,
)


class RefinementDecision(BaseModel):
    """translated note:translated note refine,translated note schema translated note"""
    needs_refinement: bool = Field(description="translated note")
    priority: str | None = Field(default=None, description="P0/P1/P2/none")
    reasoning: str = Field(description="translated note")


def create_minimax_model():
    """Minimax translated note - translated note POE API"""
    api_key = os.environ.get("POE_API_KEY")
    base_url = os.environ.get("POE_API_URL", "https://api.poe.com/v1").replace("/chat/completions", "")

    if not api_key:
        raise ValueError("POE_API_KEY not set in .env")

    # translated note OpenAIProvider translated note POE endpoint
    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key,
    )

    # POE API translated note minimax-m2.7
    return OpenAIChatModel(
        model_name="minimax-m2.7",
        provider=provider,
    )


class RefinementPipeline:
    """translated note"""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.iteration = 0
        self.decision_agent = Agent(
            create_minimax_model(),
            output_type=RefinementDecision,
            system_prompt="""translated note.

translated note:translated note Reviewer Agent translated note,translated note refine.

translated note:
- translated note schema
- translated note issue translated note
- translated note:
  1. needs_refinement
  2. priority
  3. reasoning

translated note:
- translated note issue, translated note, translated note, translated note, translated note, translated note,needs_refinement=true
- translated note"translated note".translated note loop translated note agent translated note.
- translated note/translated note,translated note refine,translated note refiner translated note.
- translated note"translated note / translated note"translated note,needs_refinement=false
- priority translated note:P0 / P1 / P2 / none
- translated note needs_refinement=true translated note,translated note P2
- translated note needs_refinement=false,translated note priority translated note none
"""
        )

    async def run(self) -> Dict[str, Any]:
        """translated note"""
        import datetime
        from pathlib import Path

        # translated note
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(f"logs/refinement/{timestamp}")
        log_dir.mkdir(parents=True, exist_ok=True)

        # translated note
        run_info = {
            "start_time": datetime.datetime.now().isoformat(),
            "max_iterations": self.max_iterations,
            "model": "minimax-m2.7",
            "pipeline_version": "V3"
        }
        (log_dir / "run_info.json").write_text(json.dumps(run_info, indent=2, ensure_ascii=False))

        print("=" * 70)
        print("KG Refinement Pipeline V3")
        print(f"translated note: {log_dir}")
        if os.environ.get("FOOD_AI_AGENT_DEBUG"):
            print(f"Agent Debug: {os.environ.get('FOOD_AI_AGENT_DEBUG')}")
        print("=" * 70)

        iteration_history = []

        for i in range(self.max_iterations):
            self.iteration = i + 1
            print(f"\n translated note {self.iteration}/{self.max_iterations}")
            print("-" * 70)

            iter_start_time = datetime.datetime.now()

            # Step 1: Review (Claude SDK)
            review_raw = await self._run_reviewer()
            if not review_raw:
                return {"success": False, "error": "Review failed"}
            print(f"   Reviewer translated note: {len(review_raw)}")

            # translated note Reviewer translated note
            iter_dir = log_dir / f"iter_{self.iteration}"
            iter_dir.mkdir(exist_ok=True)
            (iter_dir / "reviewer_raw.txt").write_text(review_raw, encoding='utf-8')

            # Step 2: translated note + translated note
            print(" pydantic-ai: translated note...")
            decision = await self.decision_agent.run(
                f"translated note Reviewer translated note refine.\n\n{review_raw[:12000]}"
            )
            decision_data = decision.output
            decision_data.priority = decision_data.priority or ("P2" if decision_data.needs_refinement else "none")

            print(f"   translated note: {'translated note' if decision_data.needs_refinement else 'translated note'} ({decision_data.priority})")

            # translated note Decision translated note
            decision_dict = decision_data.model_dump() if hasattr(decision_data, 'model_dump') else dict(decision_data)
            (iter_dir / "decision.json").write_text(
                json.dumps(decision_dict, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8'
            )

            # translated note
            iter_stats = {
                "iteration": self.iteration,
                "timestamp": iter_start_time.isoformat(),
                "needs_refinement": decision_data.needs_refinement,
                "priority": decision_data.priority,
                "reasoning": decision_data.reasoning
            }
            iteration_history.append(iter_stats)

            if not decision_data.needs_refinement:
                print(f"   translated note: {decision_data.reasoning}")
                break

            refine_candidates = select_refine_candidates(
                extract_refine_candidates_from_review(review_raw),
                limit=3,
            )
            (iter_dir / "refine_candidates.json").write_text(
                json.dumps(refine_candidates, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"   translated note: {len(refine_candidates)}")

            # Step 3: Refine (Claude SDK)
            print("🔧 translated note(translated note typed candidates)...")
            refine_result = await self._run_refiner(review_raw=review_raw, candidates=refine_candidates)
            print(
                f"   Refiner success={bool(refine_result and refine_result.get('success'))}, "
                f"response_length={len((refine_result or {}).get('agent_response', ''))}"
            )

            # translated note Refiner translated note
            if refine_result:
                (iter_dir / "refiner_result.json").write_text(
                    json.dumps(refine_result, indent=2, ensure_ascii=False, default=str),
                    encoding='utf-8'
                )

            # translated note
            if self.iteration >= self.max_iterations:
                print("Warning:  translated note")
                break

        # translated note
        summary = {
            "success": True,
            "iterations": self.iteration,
            "log_dir": str(log_dir),
            "history": iteration_history
        }
        (log_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"\n translated note,translated note {self.iteration} translated note")
        print(f"📁 translated note: {log_dir}")
        return summary

    async def _run_reviewer(self) -> str:
        """Claude Agent SDK translated note"""
        from kg_reviewer_agent import review_graph_async
        result = await review_graph_async()
        return result.get("agent_response", "") if result.get("success") else ""

    async def _run_refiner(self, review_raw: str, candidates: list[dict[str, Any]]) -> Dict:
        """Claude Agent SDK translated note
        translated note reviewer translated note typed candidates translated note refiner.
        """

        from kg_refiner_agent import refine_graph_from_candidates_async

        result = await refine_graph_from_candidates_async(review_raw=review_raw, candidates=candidates)
        return result


async def main():
    max_iterations = int(os.environ.get("FOOD_AI_REFINER_MAX_ITERATIONS", "5"))
    pipeline = RefinementPipeline(max_iterations=max_iterations)
    result = await pipeline.run()

    with open("data/pipeline_v3_result.json", 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\ntranslated note")


if __name__ == "__main__":
    asyncio.run(main())
