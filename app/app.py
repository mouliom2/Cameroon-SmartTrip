
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from nlp_parser import parse_trip_request
from planner_agent import optimize_trip
from itinerary import generate_itinerary
from simulation import run_profile_simulation, run_budget_stress_test, summarize_simulation

st.set_page_config(page_title="Cameroon SmartTrip V4", page_icon="🇨🇲", layout="wide")
st.title("🇨🇲 Cameroon SmartTrip — V4")
st.caption("Planificateur + laboratoire de simulation")

tab1, tab2, tab3 = st.tabs([
    "🧭 Planificateur",
    "🧪 Simulation de profils",
    "📉 Stress test budget"
])

with tab1:
    default_text = (
        "Nous sommes un couple avec deux enfants, budget 300 000 FCFA, "
        "3 jours à Kribi depuis Douala. Je veux un hôtel calme avec piscine "
        "près de la plage et Wi-Fi, et je veux voir les chutes de la Lobé."
    )
    request_text = st.text_area("Décrivez votre voyage", default_text, height=120)
    meal_budget = st.number_input("Budget repas total (FCFA)",0,1000000,40000,5000,key="meal")

    if st.button("✨ Planifier", type="primary", key="plan"):
        plan = optimize_trip(request_text, meal_budget_override=meal_budget)
        if plan.get("hotel"):
            st.success("Plan généré.")
            a,b,c,d = st.columns(4)
            a.metric("Hôtel",plan["hotel"])
            b.metric("Transport",plan["transport_class"])
            c.metric("Total",f"{plan['total_fcfa']:,.0f} FCFA")
            d.metric("Reste",f"{plan['remaining_fcfa']:,.0f} FCFA")

            st.subheader("Itinéraire")
            st.dataframe(pd.DataFrame(generate_itinerary(plan)), use_container_width=True)

            st.subheader("Alternatives")
            st.dataframe(pd.DataFrame(plan.get("alternatives",[])).head(10), use_container_width=True)
        else:
            st.warning(plan.get("message","Plan impossible à calculer."))

with tab2:
    st.write("Cette simulation génère des profils d'utilisateurs, tandis que les données touristiques restent celles du projet.")
    c1,c2 = st.columns(2)
    n = c1.slider("Nombre de profils",5,100,30,5)
    seed = c2.number_input("Seed",value=42,step=1)

    if st.button("▶️ Lancer la simulation", type="primary", key="profiles"):
        sims = run_profile_simulation(seed=int(seed), n=int(n))
        s = summarize_simulation(sims)

        a,b,c = st.columns(3)
        a.metric("Profils",s["n_simulations"])
        b.metric("Plans dans le budget",f"{s['success_rate']:.1%}")
        c.metric("Coût moyen",f"{s['average_total_fcfa']:,.0f} FCFA")

        st.dataframe(
            sims[[
                "simulation_id","origin","budget_fcfa","travelers","nights",
                "status","hotel","transport_class","total_fcfa","remaining_fcfa"
            ]],
            use_container_width=True
        )

        st.subheader("Hôtels les plus souvent sélectionnés")
        st.bar_chart(s["top_hotels"].set_index("hotel")["selections"])

        bands = pd.cut(
            sims["budget_fcfa"],
            bins=[0,150000,250000,350000,10_000_000],
            labels=["≤150k","150–250k","250–350k",">350k"],
            include_lowest=True
        )
        by_budget = (
            sims.assign(budget_band=bands)
            .groupby("budget_band",observed=False)
            .agg(success_rate=("within_budget","mean"))
        )
        st.subheader("Taux de réussite par budget")
        st.bar_chart(by_budget["success_rate"])

        st.download_button(
            "⬇️ Télécharger la simulation CSV",
            sims.to_csv(index=False).encode("utf-8-sig"),
            file_name="simulation_profils.csv",
            mime="text/csv"
        )

with tab3:
    c1,c2,c3 = st.columns(3)
    origin = c1.selectbox("Départ",["Douala","Yaoundé"],key="stress_origin")
    travelers = c2.number_input("Voyageurs",1,10,4,key="stress_travelers")
    nights = c3.number_input("Nuits",1,10,2,key="stress_nights")

    c4,c5,c6 = st.columns(3)
    bmin = c4.number_input("Budget min",50000,1000000,100000,25000)
    bmax = c5.number_input("Budget max",100000,3000000,600000,50000)
    bstep = c6.number_input("Pas",10000,500000,50000,10000)

    prefs = st.multiselect(
        "Préférences",
        ["Plage","Piscine","Wi-Fi","Restaurant","Famille","Petit budget","Calme","Luxe"],
        default=["Plage","Piscine","Wi-Fi","Famille"]
    )
    include_lobe = st.checkbox("Inclure les Chutes de la Lobé",True)

    if st.button("📊 Lancer le stress test",type="primary",key="stress"):
        budgets=list(range(int(bmin),int(bmax)+1,int(bstep)))
        stress=run_budget_stress_test(
            origin=origin,
            travelers=int(travelers),
            nights=int(nights),
            budgets=budgets,
            preferences=tuple(prefs),
            include_lobe=include_lobe
        )

        st.dataframe(
            stress[[
                "budget_fcfa","status","hotel","transport_class",
                "total_fcfa","remaining_fcfa","adjustments"
            ]],
            use_container_width=True
        )

        chart=stress[["budget_fcfa","total_fcfa"]].set_index("budget_fcfa")
        chart["budget_disponible"]=chart.index
        st.line_chart(chart)

        st.download_button(
            "⬇️ Télécharger le stress test CSV",
            stress.to_csv(index=False).encode("utf-8-sig"),
            file_name="stress_test_budget.csv",
            mime="text/csv"
        )

st.divider()
st.caption("Prototype : aucune disponibilité ni réservation n'est garantie. Vérifier les tarifs auprès des prestataires.")
