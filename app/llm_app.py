
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from llm_agent import run_llm_agent

st.set_page_config(page_title="SmartTrip LLM + Agent", page_icon="🤖", layout="wide")
st.title("🤖 Cameroon SmartTrip — LLM local + Agent")
st.caption("LLM local gratuit → Agent SmartTrip → SQL + recherche sémantique + optimisation")

st.info(
    "Aucune clé API payante n'est nécessaire. "
    "Mode auto : Ollama local si disponible, sinon moteur SmartTrip classique. "
    "Le mode Transformers local peut être activé séparément."
)

backend = st.selectbox(
    "Backend",
    ["auto", "ollama", "transformers", "mock"],
    index=0,
    help="mock sert à tester toute l'architecture sans télécharger de modèle."
)

query = st.text_area(
    "Votre demande",
    (
        "Nous sommes un couple avec deux enfants, budget 300 000 FCFA, "
        "3 jours à Kribi depuis Douala. Je veux un hôtel calme avec piscine "
        "près de la plage et Wi-Fi, et voir les chutes de la Lobé."
    ),
    height=130,
)
meal_budget = st.number_input("Budget repas total (FCFA)", 0, 1000000, 40000, 5000)

if st.button("🚀 Lancer LLM + Agent", type="primary"):
    try:
        result = run_llm_agent(
            query,
            meal_budget_override=int(meal_budget),
            backend_mode=backend,
        )
        st.success(f"Pipeline exécuté — backend : {result['backend']}")

        with st.expander("1️⃣ Compréhension LLM", expanded=True):
            st.json(result["llm_extracted"])
            st.caption("Requête canonique transmise à l'agent :")
            st.code(result["canonical_request"])

        plan = result["plan"]
        with st.expander("2️⃣ Décision de l'agent", expanded=True):
            if plan.get("hotel"):
                a,b,c,d = st.columns(4)
                a.metric("Hôtel", plan["hotel"])
                b.metric("Transport", plan["transport_class"])
                c.metric("Total", f"{plan['total_fcfa']:,.0f} FCFA")
                d.metric("Reste", f"{plan['remaining_fcfa']:,.0f} FCFA")
            st.json({
                "status": plan.get("status"),
                "semantic_backend": plan.get("semantic_backend"),
                "preference_score": plan.get("preference_score"),
                "adjustments": plan.get("adjustments"),
            })

        with st.expander("3️⃣ Itinéraire", expanded=True):
            st.dataframe(pd.DataFrame(result["itinerary"]), use_container_width=True)

        st.subheader("4️⃣ Réponse finale du LLM")
        st.write(result["final_answer"])

    except Exception as e:
        st.error(f"Le backend '{backend}' n'a pas pu être exécuté : {e}")
        if backend in {"ollama", "transformers"}:
            st.info("Choisissez 'mock' pour tester immédiatement toute la chaîne sans modèle externe.")
