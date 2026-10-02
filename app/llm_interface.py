
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from nlp_parser import parse_trip_request


SYSTEM_EXTRACTION = """Tu es le module de compréhension de Cameroon SmartTrip.
Retourne UNIQUEMENT un objet JSON valide avec les clés:
origin, destination, budget_fcfa, nights, travelers, rooms,
meal_budget_fcfa, preferences, requested_activities.
N'invente jamais une valeur absente. Utilise null si nécessaire.
Les préférences doivent être une liste de chaînes.
"""

SYSTEM_RESPONSE = """Tu es l'assistant Cameroon SmartTrip.
Rédige une réponse courte en français à partir UNIQUEMENT du plan JSON fourni.
N'invente aucun prix, hôtel, horaire, disponibilité ou service.
Mentionne que les tarifs doivent être revérifiés avant réservation.
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a model response."""
    text = text.strip()
    # Remove markdown fences if the local model added them.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(m.group(0))


def canonical_request(data: Dict[str, Any]) -> str:
    """Convert LLM structured output into a deterministic request understood by the existing agent."""
    origin = data.get("origin") or "Douala"
    destination = data.get("destination") or "Kribi"
    travelers = data.get("travelers")
    nights = data.get("nights")
    budget = data.get("budget_fcfa")
    rooms = data.get("rooms") or 1
    prefs = data.get("preferences") or []
    acts = data.get("requested_activities") or []

    parts = [f"Je pars de {origin} pour {destination}."]
    if travelers is not None:
        parts.append(f"Nous sommes {int(travelers)} personnes.")
    if nights is not None:
        parts.append(f"{int(nights)} nuits.")
    if budget is not None:
        parts.append(f"Budget {int(budget)} FCFA.")
    if rooms and int(rooms) > 1:
        parts.append(f"{int(rooms)} chambres.")
    if prefs:
        parts.append("Je veux " + ", ".join(str(x) for x in prefs) + ".")

    acts_text = " ".join(str(x).lower() for x in acts)
    if "lob" in acts_text or "chute" in acts_text:
        parts.append("Je veux voir les chutes de la Lobé.")
    if "phare" in acts_text:
        parts.append("Je veux visiter le phare de Kribi.")
    if "naut" in acts_text or "bateau" in acts_text or "pirogue" in acts_text:
        parts.append("Je souhaite une activité nautique.")
    if "campo" in acts_text:
        parts.append("Je veux visiter Campo Ma'an.")

    return " ".join(parts)


class BaseLLMBackend:
    name = "base"

    def extract(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError

    def compose(self, plan: Dict[str, Any]) -> str:
        raise NotImplementedError


class RuleBasedMockLLM(BaseLLMBackend):
    """
    Test backend. It behaves like an LLM interface but uses the existing parser.
    It lets the whole LLM→Agent orchestration be tested without a paid API.
    """
    name = "mock-local-test"

    def extract(self, text: str) -> Dict[str, Any]:
        req = parse_trip_request(text).to_dict()
        return {
            "origin": req.get("origin"),
            "destination": req.get("destination"),
            "budget_fcfa": req.get("budget_fcfa"),
            "nights": req.get("nights"),
            "travelers": req.get("travelers"),
            "rooms": req.get("rooms", 1),
            "meal_budget_fcfa": req.get("meal_budget_fcfa", 0),
            "preferences": req.get("preferences", []),
            "requested_activities": req.get("requested_activities", []),
        }

    def compose(self, plan: Dict[str, Any]) -> str:
        if not plan.get("hotel"):
            return f"Je n'ai pas pu construire un séjour exploitable. Statut : {plan.get('status')}."
        status = "respecte" if plan.get("status") == "ok" else "dépasse"
        return (
            f"Je propose {plan['hotel']} avec {plan['transport_class']}. "
            f"Le coût calculé est de {plan['total_fcfa']:,.0f} FCFA et le budget {status} la contrainte indiquée. "
            f"Reste estimé : {plan['remaining_fcfa']:,.0f} FCFA. "
            "Les tarifs et disponibilités doivent être revérifiés auprès des prestataires."
        )


class OllamaBackend(BaseLLMBackend):
    """Free local LLM through an Ollama server. No API key is required."""
    name = "ollama"

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None, timeout: int = 120):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        import requests

        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.1},
        }
        if json_mode:
            payload["format"] = "json"

        r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]

    def extract(self, text: str) -> Dict[str, Any]:
        response = self._chat(SYSTEM_EXTRACTION, text, json_mode=True)
        return _extract_json(response)

    def compose(self, plan: Dict[str, Any]) -> str:
        response = self._chat(
            SYSTEM_RESPONSE,
            "PLAN_JSON:\n" + json.dumps(plan, ensure_ascii=False, default=str),
            json_mode=False,
        )
        return response.strip()


class TransformersBackend(BaseLLMBackend):
    """
    Free local Hugging Face model.
    First run may download model weights, but there is no paid API key.
    """
    name = "transformers-local"

    def __init__(self, model: Optional[str] = None):
        self.model_name = model or os.getenv("LOCAL_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        self._pipe = None

    def _load(self):
        if self._pipe is None:
            from transformers import pipeline
            self._pipe = pipeline(
                "text-generation",
                model=self.model_name,
                device_map="auto",
                trust_remote_code=True,
            )

    def _generate(self, system: str, user: str, max_new_tokens: int = 350) -> str:
        self._load()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        output = self._pipe(
            messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
        )
        generated = output[0]["generated_text"]
        if isinstance(generated, list):
            return generated[-1]["content"]
        return str(generated)

    def extract(self, text: str) -> Dict[str, Any]:
        return _extract_json(self._generate(SYSTEM_EXTRACTION, text, 250))

    def compose(self, plan: Dict[str, Any]) -> str:
        return self._generate(
            SYSTEM_RESPONSE,
            "PLAN_JSON:\n" + json.dumps(plan, ensure_ascii=False, default=str),
            300,
        ).strip()


def get_backend(mode: str = "auto") -> BaseLLMBackend:
    """
    auto:
      1) Ollama if reachable
      2) Transformers if explicitly enabled by LOCAL_HF_MODEL / SMARTTRIP_USE_TRANSFORMERS=1
      3) deterministic fallback used by the original project
    """
    mode = (mode or "auto").lower()

    if mode in {"mock", "fallback", "rule"}:
        return RuleBasedMockLLM()

    if mode == "ollama":
        return OllamaBackend()

    if mode in {"transformers", "hf", "local"}:
        return TransformersBackend()

    # Auto-detect Ollama quickly.
    try:
        import requests
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        r = requests.get(f"{host}/api/tags", timeout=1.5)
        if r.ok:
            return OllamaBackend()
    except Exception:
        pass

    if os.getenv("SMARTTRIP_USE_TRANSFORMERS", "0") == "1" or os.getenv("LOCAL_HF_MODEL"):
        return TransformersBackend()

    return RuleBasedMockLLM()
