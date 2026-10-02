
from pathlib import Path
import sqlite3
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "database" / "cameroon_smarttrip.db"

def load_data():
    con = sqlite3.connect(DB_PATH)
    hotels = pd.read_sql_query("SELECT * FROM vw_budget_hotels", con)
    transport = pd.read_sql_query("SELECT * FROM transport", con)
    activities = pd.read_sql_query("SELECT * FROM activities", con)
    attractions = pd.read_sql_query("SELECT * FROM attractions", con)
    restaurants = pd.read_sql_query("SELECT * FROM restaurants", con)
    con.close()
    return hotels, transport, activities, attractions, restaurants

def preference_score(row, preferences):
    text = " ".join(str(row.get(c, "")) for c in
        ["beach_access","pool","wifi","restaurant","family_friendly","key_features"]).lower()
    score = 0
    for pref in preferences or []:
        if pref == "Plage" and any(k in text for k in ["plage","océan","mer"]): score += 2
        elif pref == "Piscine" and "oui" in str(row.get("pool","")).lower(): score += 2
        elif pref == "Wi-Fi" and ("oui" in str(row.get("wifi","")).lower() or "wifi" in text or "wi-fi" in text): score += 1
        elif pref == "Restaurant" and "oui" in str(row.get("restaurant","")).lower(): score += 1
        elif pref == "Famille" and "oui" in str(row.get("family_friendly","")).lower(): score += 1
        elif pref == "Petit budget":
            score += max(0, 5 - int(float(row["price_from_xaf"]) // 10000))
    return score

def build_options(budget_total, nights, travelers, rooms, transport_class,
                  meal_envelope=0, selected_activities=None, preferences=None):
    hotels, transport, activities, attractions, restaurants = load_data()
    selected_activities = selected_activities or []
    preferences = preferences or []

    t = transport[(transport["origin"]=="Douala") &
                  (transport["destination"]=="Kribi") &
                  (transport["service_class"]==transport_class)]
    if t.empty: raise ValueError("Transport sélectionné introuvable.")
    tr = t.iloc[0]
    transport_cost = float(tr["round_trip_price"]) * travelers

    activity_cost = 0.0
    activity_notes = []
    for act_id in selected_activities:
        r = activities[activities["activity_id"]==act_id]
        if r.empty: continue
        rr = r.iloc[0]
        if pd.notna(rr["price_from"]) and str(rr["price_currency"])=="XAF":
            activity_cost += float(rr["price_from"])
            activity_notes.append(f"{rr['name']}: {float(rr['price_from']):,.0f} FCFA (prix publié; unité exacte à confirmer)")
        else:
            activity_notes.append(f"{rr['name']}: prix non intégré au budget (non-XAF ou non publié)")

    rows=[]
    for _,h in hotels.iterrows():
        hotel_cost=float(h["price_from_xaf"])*nights*rooms
        total=hotel_cost+transport_cost+float(meal_envelope)+activity_cost
        remaining=float(budget_total)-total
        rows.append({
            "hotel_id":h["hotel_id"],"hotel":h["name"],
            "prix_nuit_fcfa":float(h["price_from_xaf"]),
            "cout_hotel_fcfa":hotel_cost,"cout_transport_fcfa":transport_cost,
            "enveloppe_repas_fcfa":float(meal_envelope),"activites_fcfa":activity_cost,
            "total_fcfa":total,"reste_budget_fcfa":remaining,
            "dans_budget":remaining>=0,"score_preferences":preference_score(h,preferences),
            "plage":h.get("beach_access"),"piscine":h.get("pool"),"wifi":h.get("wifi"),
            "restaurant":h.get("restaurant"),"famille":h.get("family_friendly"),
            "booking_url":h.get("booking_url"),"booking_note":h.get("booking_note"),
            "verified_on":h.get("verified_on"),"confidence":h.get("price_confidence")
        })
    out=pd.DataFrame(rows).sort_values(
        ["dans_budget","score_preferences","reste_budget_fcfa"],
        ascending=[False,False,True]
    ).reset_index(drop=True)
    return out, activity_notes, tr.to_dict(), attractions, restaurants

if __name__ == "__main__":
    opts,*_ = build_options(250000,2,2,1,"Business Class",30000,["ACT001"],["Plage","Piscine","Wi-Fi"])
    print(opts[["hotel","total_fcfa","reste_budget_fcfa","dans_budget","score_preferences"]].head(8).to_string(index=False))
