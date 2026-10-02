
from __future__ import annotations

import random
from typing import Iterable
import pandas as pd

from planner_agent import optimize_trip

PREFERENCE_SETS = [
    ["Plage"],
    ["Plage", "Piscine"],
    ["Plage", "Wi-Fi"],
    ["Restaurant", "Petit budget"],
    ["Famille", "Plage"],
    ["Calme", "Plage"],
    ["Luxe", "Piscine", "Restaurant"],
    ["Petit budget"],
]

ACTIVITY_PHRASES = [
    "",
    " Je veux voir les chutes de la Lobé.",
    " Je veux visiter le phare de Kribi.",
    " Je souhaite une activité nautique.",
]

def make_request(origin, budget, travelers, nights, preferences, activity_phrase=""):
    pref_text = ", ".join(preferences)
    return (
        f"Je pars de {origin} pour Kribi. Nous sommes {travelers} personnes, "
        f"{nights} nuits, budget {budget} FCFA. "
        f"Je recherche {pref_text}.{activity_phrase}"
    )

def _plan_to_row(sim_id, request_text, plan):
    req = plan.get("request", {})
    return {
        "simulation_id": sim_id,
        "request_text": request_text,
        "origin": req.get("origin"),
        "budget_fcfa": req.get("budget_fcfa"),
        "travelers": req.get("travelers"),
        "nights": req.get("nights"),
        "rooms": req.get("rooms"),
        "preferences": " | ".join(req.get("preferences", [])),
        "requested_activities": " | ".join(req.get("requested_activities", [])),
        "status": plan.get("status"),
        "hotel": plan.get("hotel"),
        "transport_class": plan.get("transport_class"),
        "hotel_price_night": plan.get("hotel_price_night"),
        "hotel_cost_fcfa": plan.get("hotel_cost_fcfa"),
        "transport_cost_fcfa": plan.get("transport_cost_fcfa"),
        "activity_cost_fcfa": plan.get("activity_cost_fcfa"),
        "meal_budget_fcfa": plan.get("meal_budget_fcfa"),
        "total_fcfa": plan.get("total_fcfa"),
        "remaining_fcfa": plan.get("remaining_fcfa"),
        "within_budget": plan.get("status") == "ok",
        "preference_score": plan.get("preference_score"),
        "semantic_score": plan.get("semantic_score"),
        "semantic_backend": plan.get("semantic_backend"),
        "adjustments": " | ".join(plan.get("adjustments", [])),
    }

def run_profile_simulation(seed=42, n=30):
    """
    Simule des profils de voyageurs.
    Les données touristiques restent celles du projet.
    """
    rng = random.Random(seed)
    rows = []

    for i in range(1, n + 1):
        origin = rng.choice(["Douala", "Yaoundé"])
        budget = rng.choice([100000,120000,150000,180000,220000,250000,300000,350000,450000,600000])
        travelers = rng.choice([1,2,2,2,3,4,4,5])
        nights = rng.choice([1,2,2,3,3,4])
        prefs = rng.choice(PREFERENCE_SETS)
        activity = rng.choice(ACTIVITY_PHRASES)

        request = make_request(origin, budget, travelers, nights, prefs, activity)
        meal_budget = 10000 * travelers * max(1, nights)

        plan = optimize_trip(request, meal_budget_override=meal_budget)
        rows.append(_plan_to_row(f"SIM{i:03d}", request, plan))

    return pd.DataFrame(rows)

def run_budget_stress_test(
    origin="Douala",
    travelers=4,
    nights=2,
    budgets: Iterable[int] = (100000,125000,150000,175000,200000,250000,300000,400000,500000),
    preferences=("Plage","Piscine","Wi-Fi","Famille"),
    include_lobe=True,
):
    """
    Teste le même profil avec différents budgets.
    """
    rows = []
    activity = " Je veux voir les chutes de la Lobé." if include_lobe else ""
    pref_text = ", ".join(preferences)

    for budget in budgets:
        request = (
            f"Je pars de {origin} pour Kribi. Nous sommes {travelers} personnes, "
            f"{nights} nuits, budget {budget} FCFA. "
            f"Je veux {pref_text}.{activity}"
        )
        meal_budget = 10000 * travelers * max(1, nights)
        plan = optimize_trip(request, meal_budget_override=meal_budget)
        rows.append(_plan_to_row(f"BUDGET_{budget}", request, plan))

    return pd.DataFrame(rows)

def summarize_simulation(df):
    return {
        "n_simulations": int(len(df)),
        "success_rate": float((df["status"] == "ok").mean()) if len(df) else 0.0,
        "average_total_fcfa": float(pd.to_numeric(df["total_fcfa"], errors="coerce").mean()) if len(df) else 0.0,
        "top_hotels": df["hotel"].dropna().value_counts().head(5).rename_axis("hotel").reset_index(name="selections"),
        "top_transport": df["transport_class"].dropna().value_counts().rename_axis("transport_class").reset_index(name="selections"),
    }

if __name__ == "__main__":
    profiles = run_profile_simulation(seed=42, n=20)
    stress = run_budget_stress_test()
    print(profiles[["simulation_id","budget_fcfa","status","hotel","transport_class","total_fcfa","remaining_fcfa"]].to_string(index=False))
    print()
    print(stress[["budget_fcfa","status","hotel","transport_class","total_fcfa","remaining_fcfa","adjustments"]].to_string(index=False))
