
from pathlib import Path
import sqlite3
from itertools import combinations
import pandas as pd

from nlp_parser import parse_trip_request
from semantic_search import HotelSemanticSearch

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "database" / "cameroon_smarttrip.db"

ACTIVITY_ALIASES = {
    "Chutes de la Lobé":"ACT001",
    "Camp pygmée":"ACT002",
    "Nautisme":"ACT003",
    "Campo Ma'an":"ACT005",
}

def _load():
    con = sqlite3.connect(DB_PATH)
    hotels = pd.read_sql_query("SELECT * FROM vw_budget_hotels", con)
    transport = pd.read_sql_query("SELECT * FROM transport", con)
    activities = pd.read_sql_query("SELECT * FROM activities", con)
    attractions = pd.read_sql_query("SELECT * FROM attractions", con)
    restaurants = pd.read_sql_query("SELECT * FROM restaurants", con)
    con.close()
    return hotels, transport, activities, attractions, restaurants

def _activity_subsets(requested_ids):
    # Preserve explicitly requested activity when possible, but allow dropping
    # activities if the budget cannot be respected.
    requested_ids = list(dict.fromkeys(requested_ids))
    subsets = [requested_ids]
    for n in range(len(requested_ids)-1, -1, -1):
        for combo in combinations(requested_ids, n):
            c = list(combo)
            if c not in subsets:
                subsets.append(c)
    return subsets

def _preference_score(row, prefs):
    text = " ".join(str(row.get(k,"")) for k in [
        "beach_access","pool","wifi","restaurant","family_friendly","key_features","booking_note"
    ]).lower()
    score=0
    for p in prefs:
        if p=="Plage" and any(x in text for x in ["plage","océan","ocean","mer"]): score += 3
        elif p=="Piscine" and "oui" in str(row.get("pool","")).lower(): score += 3
        elif p=="Wi-Fi" and any(x in text for x in ["wifi","wi-fi"]): score += 2
        elif p=="Restaurant" and "oui" in str(row.get("restaurant","")).lower(): score += 2
        elif p=="Famille" and "oui" in str(row.get("family_friendly","")).lower(): score += 2
        elif p=="Calme" and any(x in text for x in ["calme","paisible","jardin","nature"]): score += 2
        elif p=="Luxe" and any(x in text for x in ["luxe","premium","resort","suite","spa"]): score += 2
        elif p=="Petit budget":
            try:
                px=float(row.get("price_from_xaf"))
                score += max(0, 5-int(px//10000))
            except Exception:
                pass
    return score

def _activity_cost(activities, ids):
    cost=0.0
    notes=[]
    for act_id in ids:
        r=activities[activities["activity_id"]==act_id]
        if r.empty: continue
        x=r.iloc[0]
        if pd.notna(x["price_from"]) and str(x["price_currency"])=="XAF":
            cost += float(x["price_from"])
            notes.append(f"{x['name']} — {float(x['price_from']):,.0f} FCFA (prix public; unité à confirmer)")
        else:
            notes.append(f"{x['name']} — tarif non intégré au calcul")
    return cost, notes

def optimize_trip(request_text: str, meal_budget_override=None):
    req = parse_trip_request(request_text)
    if req.budget_fcfa is None or req.nights is None or req.travelers is None:
        return {
            "status":"needs_input",
            "request":req.to_dict(),
            "message":"Budget, durée et nombre de voyageurs doivent être précisés."
        }

    hotels, transport, activities, attractions, restaurants = _load()
    t = transport[
        (transport["origin"]==req.origin) &
        (transport["destination"]=="Kribi")
    ].copy()
    if t.empty:
        return {"status":"unsupported_origin","request":req.to_dict(),"message":f"Aucun transport réel intégré depuis {req.origin}."}

    # Free text hotel ranking.
    semantic = HotelSemanticSearch()
    sem = semantic.search(request_text, top_k=len(hotels))[["hotel_id","semantic_score"]]
    hotels = hotels.merge(sem, on="hotel_id", how="left")
    hotels["preference_score"] = hotels.apply(lambda r:_preference_score(r, req.preferences), axis=1)
    hotels["combined_score"] = hotels["preference_score"] + hotels["semantic_score"].fillna(0)*4

    requested_ids=[ACTIVITY_ALIASES[x] for x in req.requested_activities if x in ACTIVITY_ALIASES]
    activity_sets=_activity_subsets(requested_ids)

    meal_budget = req.meal_budget_fcfa if meal_budget_override is None else meal_budget_override
    candidates=[]
    for _,tr in t.iterrows():
        transport_cost=float(tr["round_trip_price"])*req.travelers
        for _,h in hotels.iterrows():
            hotel_cost=float(h["price_from_xaf"])*req.nights*req.rooms
            for act_ids in activity_sets:
                act_cost, act_notes=_activity_cost(activities,act_ids)
                total=transport_cost+hotel_cost+act_cost+meal_budget
                remaining=req.budget_fcfa-total
                candidates.append({
                    "hotel_id":h["hotel_id"],"hotel":h["name"],
                    "transport_class":tr["service_class"],
                    "transport_cost_fcfa":transport_cost,
                    "hotel_cost_fcfa":hotel_cost,
                    "activity_cost_fcfa":act_cost,
                    "meal_budget_fcfa":meal_budget,
                    "total_fcfa":total,
                    "remaining_fcfa":remaining,
                    "within_budget":remaining>=0,
                    "kept_activity_ids":act_ids,
                    "activity_notes":act_notes,
                    "combined_score":float(h["combined_score"]),
                    "semantic_score":float(h["semantic_score"]),
                    "preference_score":int(h["preference_score"]),
                    "hotel_price_night":float(h["price_from_xaf"]),
                    "booking_url":h.get("booking_url"),
                    "booking_note":h.get("booking_note"),
                    "verified_on":h.get("verified_on"),
                    "confidence":h.get("price_confidence"),
                    "departures":tr["departures"],
                    "transport_source":tr["source_url"],
                })

    df=pd.DataFrame(candidates)
    feasible=df[df["within_budget"]].copy()
    if len(feasible):
        # Prefer semantic/preference fit; then use budget efficiently, not necessarily cheapest.
        feasible["budget_utilization"] = feasible["total_fcfa"] / req.budget_fcfa
        feasible=feasible.sort_values(
            ["combined_score","budget_utilization","hotel_price_night"],
            ascending=[False,False,True]
        )
        best=feasible.iloc[0].to_dict()
        status="ok"
    else:
        # Return closest possible plan.
        df["overrun"]=df["total_fcfa"]-req.budget_fcfa
        df=df.sort_values(["overrun","combined_score"],ascending=[True,False])
        best=df.iloc[0].to_dict()
        status="over_budget"

    adjustments=[]
    requested_set=set(requested_ids)
    kept_set=set(best["kept_activity_ids"])
    removed=requested_set-kept_set
    if removed:
        names={v:k for k,v in ACTIVITY_ALIASES.items()}
        adjustments.append("Activité(s) retirée(s) pour respecter le budget : " + ", ".join(names.get(x,x) for x in removed))
    if best["transport_class"]!="MasterClass Plus":
        adjustments.append(f"Transport retenu : {best['transport_class']} pour mieux équilibrer le budget.")
    if meal_budget==0:
        adjustments.append("Repas non budgétés : le total affiché n'inclut pas la restauration.")

    best["adjustments"]=adjustments
    best["semantic_backend"]=semantic.backend
    best["request"]=req.to_dict()
    best["status"]=status
    best["alternatives"]=feasible.head(5).to_dict("records") if len(feasible) else df.head(5).to_dict("records")
    return best

if __name__ == "__main__":
    q="Nous sommes un couple avec deux enfants, budget 300 000 FCFA, 3 jours à Kribi depuis Douala, hôtel calme avec piscine près de la plage et Wi-Fi, je veux voir les chutes de la Lobé."
    result=optimize_trip(q, meal_budget_override=40000)
    print("STATUS:",result["status"])
    print("HOTEL:",result.get("hotel"))
    print("TRANSPORT:",result.get("transport_class"))
    print("TOTAL:",result.get("total_fcfa"))
    print("RESTE:",result.get("remaining_fcfa"))
    print("BACKEND:",result.get("semantic_backend"))
