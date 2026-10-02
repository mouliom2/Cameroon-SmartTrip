
from __future__ import annotations

from typing import Any, Dict, Optional

from llm_interface import get_backend, canonical_request, BaseLLMBackend
from planner_agent import optimize_trip
from itinerary import generate_itinerary


def run_llm_agent(
    user_text: str,
    meal_budget_override: Optional[int] = None,
    backend_mode: str = "auto",
    backend: Optional[BaseLLMBackend] = None,
) -> Dict[str, Any]:
    """
    Full pipeline:
      User -> Local LLM -> structured intent -> existing SmartTrip Agent
      -> SQL/semantic/budget tools -> local LLM -> final answer
    """
    llm = backend or get_backend(backend_mode)

    extracted = llm.extract(user_text)
    canonical = canonical_request(extracted)

    if meal_budget_override is None:
        meal_budget_override = extracted.get("meal_budget_fcfa")
        if meal_budget_override is None:
            meal_budget_override = 0

    plan = optimize_trip(
        canonical,
        meal_budget_override=int(meal_budget_override or 0),
    )

    itinerary = generate_itinerary(plan) if plan.get("hotel") else []
    final_answer = llm.compose(plan)

    return {
        "backend": llm.name,
        "user_text": user_text,
        "llm_extracted": extracted,
        "canonical_request": canonical,
        "plan": plan,
        "itinerary": itinerary,
        "final_answer": final_answer,
    }


if __name__ == "__main__":
    q = (
        "Nous sommes un couple avec deux enfants, budget 300 000 FCFA, "
        "3 jours à Kribi depuis Douala. Je veux un hôtel avec piscine près "
        "de la plage et Wi-Fi, et voir les chutes de la Lobé."
    )
    result = run_llm_agent(q, meal_budget_override=40000, backend_mode="mock")
    print("BACKEND:", result["backend"])
    print("EXTRACTION:", result["llm_extracted"])
    print("PLAN:", result["plan"].get("hotel"), result["plan"].get("total_fcfa"))
    print("RÉPONSE:", result["final_answer"])
