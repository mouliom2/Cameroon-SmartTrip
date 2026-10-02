from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from nlp_parser import parse_trip_request
from planner_agent import optimize_trip
from simulation import run_budget_stress_test

def test_parser():
    req = parse_trip_request(
        "Nous sommes 2 personnes, 2 nuits à Kribi depuis Douala, budget 220000 FCFA, plage et wifi."
    )
    assert req.origin == "Douala"
    assert req.destination == "Kribi"
    assert req.travelers == 2
    assert req.nights == 2
    assert req.budget_fcfa == 220000

def test_planner():
    plan = optimize_trip(
        "Nous sommes 2 personnes, 2 nuits à Kribi depuis Douala, budget 300000 FCFA, plage et wifi.",
        meal_budget_override=30000
    )
    assert plan.get("status") in {"ok", "over_budget"}
    assert plan.get("hotel") is not None

def test_stress():
    df = run_budget_stress_test(budgets=[150000, 250000, 350000])
    assert len(df) == 3
    assert "hotel" in df.columns
