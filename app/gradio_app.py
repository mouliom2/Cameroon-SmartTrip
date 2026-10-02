
from pathlib import Path
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import gradio as gr

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from llm_agent import run_llm_agent
from simulation import run_profile_simulation, run_budget_stress_test, summarize_simulation

PREFS = ["Plage", "Piscine", "Wi-Fi", "Restaurant", "Famille", "Petit budget", "Calme", "Luxe"]

def _build_query(origin, budget, travelers, nights, prefs, include_lobe):
    pref_text = ", ".join(prefs or []) if prefs else "un séjour agréable"
    extra = " Je veux voir les chutes de la Lobé." if include_lobe else ""
    return (
        f"Je pars de {origin} pour Kribi. Nous sommes {int(travelers)} personnes, "
        f"{int(nights)} nuits, budget {int(budget)} FCFA. "
        f"Je veux {pref_text}.{extra}"
    )

def plan_trip(origin, budget, travelers, nights, meal_budget, prefs, include_lobe, free_text, backend):
    query = free_text.strip() if free_text and free_text.strip() else _build_query(
        origin, budget, travelers, nights, prefs, include_lobe
    )

    result = run_llm_agent(
        query,
        meal_budget_override=int(meal_budget),
        backend_mode=backend
    )

    plan = result["plan"]
    extracted = result["llm_extracted"]

    if not plan.get("hotel"):
        summary = f"### Aucun plan exploitable\n\nStatut : **{plan.get('status')}**"
        return summary, extracted, pd.DataFrame(), pd.DataFrame(), result["final_answer"]

    status = "✅ Budget respecté" if plan.get("status") == "ok" else "⚠️ Budget dépassé"

    summary = f"""
### {status}

**Hôtel :** {plan['hotel']}  
**Transport :** {plan['transport_class']}  
**Coût total :** {plan['total_fcfa']:,.0f} FCFA  
**Reste estimé :** {plan['remaining_fcfa']:,.0f} FCFA  
**Backend LLM :** {result['backend']}  
**Moteur sémantique :** {plan.get('semantic_backend')}  
"""

    itinerary = pd.DataFrame(result["itinerary"])
    alternatives = pd.DataFrame(plan.get("alternatives", []))
    if not alternatives.empty:
        wanted = [c for c in [
            "hotel", "transport_class", "hotel_price_night",
            "total_fcfa", "remaining_fcfa", "combined_score", "confidence"
        ] if c in alternatives.columns]
        alternatives = alternatives[wanted].head(10)

    return summary, extracted, itinerary, alternatives, result["final_answer"]

def simulate_profiles(n, seed):
    df = run_profile_simulation(seed=int(seed), n=int(n))
    s = summarize_simulation(df)

    summary = f"""
### Résultats
- **Profils simulés :** {s['n_simulations']}
- **Plans dans le budget :** {s['success_rate']:.1%}
- **Coût moyen :** {s['average_total_fcfa']:,.0f} FCFA
"""

    hotel_counts = df["hotel"].value_counts().head(8)

    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.barh(hotel_counts.index[::-1], hotel_counts.values[::-1])
    ax.set_xlabel("Nombre de sélections")
    ax.set_title("Hôtels les plus retenus")
    fig.tight_layout()

    cols = [c for c in [
        "simulation_id","origin","budget_fcfa","travelers","nights",
        "status","hotel","transport_class","total_fcfa","remaining_fcfa"
    ] if c in df.columns]

    return summary, df[cols], fig

def stress_test(origin, travelers, nights, bmin, bmax, bstep, prefs, include_lobe):
    budgets = list(range(int(bmin), int(bmax)+1, int(bstep)))
    df = run_budget_stress_test(
        origin=origin,
        travelers=int(travelers),
        nights=int(nights),
        budgets=budgets,
        preferences=tuple(prefs or []),
        include_lobe=bool(include_lobe)
    )

    fig, ax = plt.subplots(figsize=(8,4.5))
    ax.plot(df["budget_fcfa"], df["total_fcfa"], marker="o", label="Coût du plan")
    ax.plot(df["budget_fcfa"], df["budget_fcfa"], linestyle="--", label="Budget")
    ax.set_xlabel("Budget (FCFA)")
    ax.set_ylabel("FCFA")
    ax.set_title("Stress test budgétaire")
    ax.legend()
    fig.tight_layout()

    cols = [c for c in [
        "budget_fcfa","status","hotel","transport_class",
        "total_fcfa","remaining_fcfa","adjustments"
    ] if c in df.columns]
    return df[cols], fig

with gr.Blocks(title="Cameroon SmartTrip — LLM + Agent") as demo:
    gr.Markdown(
        "# 🇨🇲 Cameroon SmartTrip — LLM local + Agent\n"
        "Application de planification touristique, simulation et stress test."
    )

    with gr.Tab("🤖 Planification LLM + Agent"):
        with gr.Row():
            origin = gr.Dropdown(["Douala","Yaoundé"], value="Douala", label="Départ")
            budget = gr.Number(value=300000, label="Budget total (FCFA)")
            travelers = gr.Number(value=4, precision=0, label="Voyageurs")
            nights = gr.Number(value=2, precision=0, label="Nuits")

        with gr.Row():
            meals = gr.Number(value=40000, label="Budget repas")
            prefs = gr.CheckboxGroup(PREFS, value=["Plage","Piscine","Wi-Fi","Famille"], label="Préférences")
            lobe = gr.Checkbox(value=True, label="Inclure les Chutes de la Lobé")
            backend = gr.Dropdown(
                ["mock", "auto", "ollama", "transformers"],
                value="mock",
                label="Backend LLM"
            )

        free_text = gr.Textbox(
            label="Demande libre (facultatif)",
            placeholder="Ex. Nous sommes un couple avec deux enfants, budget 300 000 FCFA..."
        )

        run = gr.Button("🚀 Lancer LLM + Agent", variant="primary")
        summary = gr.Markdown()
        extracted = gr.JSON(label="Compréhension LLM")
        itinerary = gr.Dataframe(label="Itinéraire")
        alternatives = gr.Dataframe(label="Alternatives")
        final_answer = gr.Textbox(label="Réponse finale du LLM", lines=6)

        run.click(
            plan_trip,
            inputs=[origin,budget,travelers,nights,meals,prefs,lobe,free_text,backend],
            outputs=[summary,extracted,itinerary,alternatives,final_answer]
        )

    with gr.Tab("🧪 Simulation de profils"):
        with gr.Row():
            n = gr.Slider(5,100,value=30,step=5,label="Nombre de profils")
            seed = gr.Number(value=42,precision=0,label="Seed")
        btn_sim = gr.Button("▶️ Lancer la simulation", variant="primary")
        sim_summary = gr.Markdown()
        sim_table = gr.Dataframe(label="Résultats")
        sim_plot = gr.Plot(label="Hôtels les plus retenus")
        btn_sim.click(simulate_profiles, [n,seed], [sim_summary,sim_table,sim_plot])

    with gr.Tab("📉 Stress test"):
        with gr.Row():
            s_origin = gr.Dropdown(["Douala","Yaoundé"], value="Douala", label="Départ")
            s_travelers = gr.Number(value=4, precision=0, label="Voyageurs")
            s_nights = gr.Number(value=2, precision=0, label="Nuits")
        with gr.Row():
            bmin = gr.Number(value=100000, label="Budget minimum")
            bmax = gr.Number(value=600000, label="Budget maximum")
            bstep = gr.Number(value=50000, label="Pas")
        s_prefs = gr.CheckboxGroup(PREFS, value=["Plage","Piscine","Wi-Fi","Famille"], label="Préférences")
        s_lobe = gr.Checkbox(value=True, label="Inclure Lobé")
        btn_stress = gr.Button("📊 Lancer le stress test", variant="primary")
        stress_table = gr.Dataframe(label="Décisions de l'agent")
        stress_plot = gr.Plot(label="Budget vs coût")
        btn_stress.click(
            stress_test,
            [s_origin,s_travelers,s_nights,bmin,bmax,bstep,s_prefs,s_lobe],
            [stress_table,stress_plot]
        )

    gr.Markdown(
        "**Important :** les tarifs sont datés et doivent être revérifiés avant réservation. "
        "Le mode `mock` permet de tester gratuitement toute l'architecture. "
        "Les modes Ollama/Transformers utilisent un vrai LLM local."
    )

def launch(share=False):
    return demo.launch(share=share)

if __name__ == "__main__":
    demo.launch()
