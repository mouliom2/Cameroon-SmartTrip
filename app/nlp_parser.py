
import re
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class TripRequest:
    raw_text: str
    origin: str = "Douala"
    destination: str = "Kribi"
    budget_fcfa: Optional[int] = None
    nights: Optional[int] = None
    travelers: Optional[int] = None
    rooms: int = 1
    meal_budget_fcfa: int = 0
    preferences: tuple = ()
    requested_activities: tuple = ()
    notes: tuple = ()

    def to_dict(self):
        d = asdict(self)
        d["preferences"] = list(self.preferences)
        d["requested_activities"] = list(self.requested_activities)
        d["notes"] = list(self.notes)
        return d

NUM_WORDS = {
    "un":1, "une":1, "deux":2, "trois":3, "quatre":4, "cinq":5, "six":6,
    "sept":7, "huit":8, "neuf":9, "dix":10, "onze":11, "douze":12
}

def _clean_amount(s: str) -> int:
    s = s.lower().strip().replace("\u202f"," ").replace("\xa0"," ")
    mult = 1
    if "million" in s:
        mult = 1_000_000
        s = s.replace("millions","").replace("million","")
    elif re.search(r"\b(k|mille)\b", s):
        mult = 1_000
        s = re.sub(r"\b(k|mille)\b","",s)
    digits = re.sub(r"[^\d,.]","",s).replace(" ","")
    if not digits:
        return 0
    digits = digits.replace(",", ".")
    if mult > 1 and "." in digits:
        return int(float(digits)*mult)
    return int(re.sub(r"[^\d]","",digits))*mult

def _find_number(text, pattern):
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    token = m.group(1).lower()
    if token.isdigit():
        return int(token)
    return NUM_WORDS.get(token)

def parse_trip_request(text: str) -> TripRequest:
    raw = text.strip()
    t = raw.lower().replace("yaounde","yaoundé")
    notes = []

    origin = "Yaoundé" if "yaoundé" in t else "Douala" if "douala" in t else "Douala"
    destination = "Kribi"
    if "limbe" in t or "limbé" in t or "bafoussam" in t or "dschang" in t:
        notes.append("La V3 ne planifie pour le moment que les séjours vers Kribi.")

    # Budget: prioritized around words budget / fcfa / cfa
    budget = None
    candidates = re.findall(
        r"(?:budget(?: total)?(?: de|:)?\s*)?(\d[\d\s.,]*(?:k|mille|million(?:s)?)?)\s*(?:fcfa|f\s*cfa|cfa)",
        t, re.I
    )
    if candidates:
        vals = [_clean_amount(x) for x in candidates]
        vals = [v for v in vals if v >= 10_000]
        if vals:
            budget = max(vals)
    if budget is None:
        m = re.search(r"budget(?: total)?(?: de|:)?\s*(\d[\d\s.,]*(?:k|mille|million(?:s)?)?)", t)
        if m:
            budget = _clean_amount(m.group(1))

    # Nights / days
    nights = _find_number(t, r"(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s*nuit")
    if nights is None:
        days = _find_number(t, r"(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s*jour")
        if days is not None:
            nights = max(1, days-1)
            notes.append(f"{days} jour(s) interprété(s) comme {nights} nuit(s).")

    # Travelers
    travelers = _find_number(t, r"(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze)\s*(?:personnes?|voyageurs?|adultes?)")
    family = _find_number(t, r"famille de\s*(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit)")
    if family:
        travelers = family
    children = _find_number(t, r"(\d+|un|une|deux|trois|quatre|cinq|six)\s*enfants?")
    if "couple" in t:
        travelers = 2 + (children or 0)
    elif travelers is None and children and ("avec" in t or "famille" in t):
        travelers = 2 + children

    # Rooms
    rooms = _find_number(t, r"(\d+|un|une|deux|trois|quatre|cinq)\s*chambres?")
    rooms = rooms or 1

    # Meal budget
    meal_budget = 0
    m = re.search(r"(?:repas|restauration|manger)[^\d]{0,20}(\d[\d\s.,]*(?:k|mille)?)\s*(?:fcfa|cfa)", t)
    if m:
        meal_budget = _clean_amount(m.group(1))

    # Preferences and synonyms
    pref_map = {
        "Plage":["plage","mer","océan","ocean","bord de mer"],
        "Piscine":["piscine"],
        "Wi-Fi":["wifi","wi-fi","internet"],
        "Restaurant":["restaurant","restauration"],
        "Famille":["famille","familial","enfant","enfants"],
        "Petit budget":["pas cher","moins cher","économique","economique","petit budget","bon marché","bon marche"],
        "Calme":["calme","paisible","tranquille","repos"],
        "Luxe":["luxe","haut de gamme","confort premium","premium"],
    }
    preferences=[]
    for label, words in pref_map.items():
        if any(w in t for w in words):
            preferences.append(label)

    # Activities
    acts=[]
    act_map = {
        "Chutes de la Lobé":["lobé","lobe","chutes"],
        "Camp pygmée":["pygmée","pygmee","camp des pygmées"],
        "Nautisme":["nautique","kayak","pirogue","bateau"],
        "Campo Ma'an":["campo ma'an","campo maan","parc"],
        "Phare de Kribi":["phare"],
    }
    for label, words in act_map.items():
        if any(w in t for w in words):
            acts.append(label)

    if budget is None:
        notes.append("Budget non détecté.")
    if nights is None:
        notes.append("Durée non détectée.")
    if travelers is None:
        notes.append("Nombre de voyageurs non détecté.")

    return TripRequest(
        raw_text=raw, origin=origin, destination=destination,
        budget_fcfa=budget, nights=nights, travelers=travelers,
        rooms=rooms, meal_budget_fcfa=meal_budget,
        preferences=tuple(preferences),
        requested_activities=tuple(acts),
        notes=tuple(notes)
    )

if __name__ == "__main__":
    examples = [
        "Nous sommes un couple avec deux enfants, budget 300 000 FCFA, 3 jours à Kribi, hôtel avec piscine près de la plage et Wi-Fi.",
        "Je pars de Yaoundé pour Kribi, 2 personnes, 2 nuits, budget 220000 CFA, je veux du calme et voir les chutes de la Lobé.",
    ]
    for e in examples:
        print(parse_trip_request(e).to_dict())
