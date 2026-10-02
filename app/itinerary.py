
from pathlib import Path
import sqlite3
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DB_PATH=BASE/"data"/"database"/"cameroon_smarttrip.db"

def generate_itinerary(plan):
    req=plan["request"]
    nights=int(req["nights"])
    days=nights+1
    con=sqlite3.connect(DB_PATH)
    attractions=pd.read_sql_query("SELECT * FROM attractions",con)
    activities=pd.read_sql_query("SELECT * FROM activities",con)
    restaurants=pd.read_sql_query("SELECT * FROM restaurants",con)
    con.close()

    by_name={x["name"]:x for _,x in attractions.iterrows()}
    program=[]
    program.append({
        "day":1,
        "title":f"{req['origin']} → Kribi",
        "morning":f"Départ avec MEN TRAVEL — {plan['transport_class']}.",
        "afternoon":f"Installation à {plan['hotel']}.",
        "evening":"Plage / repos. Restauration selon votre enveloppe.",
    })

    pool=[
        ("Chutes de la Lobé","Nature"),
        ("Phare de Kribi (Margaret)","Patrimoine"),
        ("Plages de Grand Batanga","Plage"),
        ("Plage de Ngoyè","Plage"),
        ("Londji - village des pêcheurs","Culture"),
    ]
    idx=0
    for day in range(2,days):
        a1=pool[idx%len(pool)][0]; idx+=1
        a2=pool[idx%len(pool)][0]; idx+=1
        program.append({
            "day":day,
            "title":"Découverte de Kribi",
            "morning":a1,
            "afternoon":a2,
            "evening":"Dîner / temps libre. Vérifier les horaires et conditions d'accès le jour même.",
        })

    if days>1:
        program.append({
            "day":days,
            "title":"Dernière découverte et retour",
            "morning":"Temps libre, plage ou achats locaux selon l'horaire de départ.",
            "afternoon":f"Retour Kribi → {req['origin']} avec MEN TRAVEL.",
            "evening":"Fin du séjour.",
        })

    # Avoid duplicate day 1/day final when 1-night stay creates 2 days; fine.
    return program[:days]

def itinerary_markdown(program):
    lines=[]
    for d in program:
        lines += [
            f"## Jour {d['day']} — {d['title']}",
            f"- **Matin :** {d['morning']}",
            f"- **Après-midi :** {d['afternoon']}",
            f"- **Soir :** {d['evening']}",
            ""
        ]
    return "\n".join(lines)
