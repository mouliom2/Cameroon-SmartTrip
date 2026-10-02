
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from llm_interface import RuleBasedMockLLM, canonical_request
from llm_agent import run_llm_agent


def test_mock_llm_extracts_structure():
    llm = RuleBasedMockLLM()
    data = llm.extract(
        "Nous sommes 2 personnes, 2 nuits à Kribi depuis Douala, "
        "budget 220000 FCFA, plage et wifi."
    )
    assert data["origin"] == "Douala"
    assert data["travelers"] == 2
    assert data["nights"] == 2
    assert data["budget_fcfa"] == 220000


def test_canonical_request():
    text = canonical_request({
        "origin":"Yaoundé",
        "destination":"Kribi",
        "travelers":2,
        "nights":3,
        "budget_fcfa":250000,
        "rooms":1,
        "preferences":["Plage","Restaurant"],
        "requested_activities":["Chutes de la Lobé"],
    })
    assert "Yaoundé" in text
    assert "250000 FCFA" in text
    assert "chutes de la Lobé" in text


def test_llm_agent_full_pipeline_mock():
    result = run_llm_agent(
        "Nous sommes 2 personnes, 2 nuits à Kribi depuis Douala, "
        "budget 300000 FCFA, plage, piscine et wifi.",
        meal_budget_override=30000,
        backend_mode="mock",
    )
    assert result["backend"] == "mock-local-test"
    assert result["plan"].get("hotel") is not None
    assert result["plan"].get("status") in {"ok","over_budget"}
    assert len(result["final_answer"]) > 20
