# 🇨🇲 Cameroon SmartTrip

**AI-assisted travel planning prototype for Cameroon using traceable real-world tourism data.**

Cameroon SmartTrip is a portfolio and MVP-oriented project that combines **data engineering, SQLite, natural-language parsing, semantic search, budget optimization, simulation, and interactive apps** to propose tourism plans for trips to Kribi.

The current prototype supports departures from **Douala** and **Yaoundé** and uses public, source-traceable data for hotels, transport, activities, attractions, and restaurants.

---

## Why this project?

Travel planning in Cameroon is often fragmented across multiple websites, agencies, hotels, and informal sources. Cameroon SmartTrip explores how a lightweight intelligent agent can:

- understand a travel request written in French;
- extract budget, duration, travelers, origin, and preferences;
- search accommodation data semantically;
- compare several transport / hotel / activity combinations;
- keep the trip within budget when possible;
- generate a day-by-day itinerary;
- simulate many traveler profiles;
- run budget stress tests;
- expose results through Streamlit, Gradio, and Google Colab.

---

## Current features

- Natural-language trip parsing in French
- Budget and constraint extraction
- Semantic hotel search
- TF-IDF fallback with no API key
- Optional multilingual Sentence Transformers embeddings
- SQLite tourism database
- Budget optimization
- Day-by-day itinerary generation
- Multi-profile simulation
- Budget stress testing
- Streamlit application
- Gradio simulation application
- Google Colab notebooks
- Data provenance and verification dates

---

## Example request

> Nous sommes un couple avec deux enfants, budget 300 000 FCFA, 3 jours à Kribi depuis Douala. Je veux un hôtel calme avec piscine près de la plage et Wi-Fi, et je veux voir les chutes de la Lobé.

The planner extracts the constraints, ranks possible hotels, evaluates transport and activities, and returns a feasible plan when one exists.

---

## Repository structure

```text
Cameroon-SmartTrip/
├── app/
│   ├── app.py
│   ├── gradio_app.py
│   ├── itinerary.py
│   ├── nlp_parser.py
│   ├── planner_agent.py
│   ├── recommender.py
│   ├── semantic_search.py
│   └── simulation.py
├── data/
│   ├── raw/
│   └── database/
│       └── cameroon_smarttrip.db
├── docs/
│   ├── architecture_v3.md
│   ├── data_dictionary.md
│   ├── data_quality.md
│   ├── roadmap.md
│   └── simulation_report.md
├── notebooks/
│   ├── Cameroon_SmartTrip_Colab.ipynb
│   ├── Cameroon_SmartTrip_Simulation_Colab.ipynb
│   └── Cameroon_SmartTrip_Application_Simulation_Colab.ipynb
├── simulation_results/
├── sql/
├── tests/
├── .github/workflows/
├── requirements.txt
├── requirements_colab.txt
├── requirements_embeddings.txt
├── LICENSE
└── README.md
```

---

## Run locally

```bash
git clone <YOUR_REPOSITORY_URL>
cd Cameroon-SmartTrip
pip install -r requirements.txt
streamlit run app/app.py
```

For the Gradio simulation app:

```bash
python app/gradio_app.py
```

---

## Run in Google Colab

Open:

- `notebooks/Cameroon_SmartTrip_Colab.ipynb`
- `notebooks/Cameroon_SmartTrip_Simulation_Colab.ipynb`
- `notebooks/Cameroon_SmartTrip_Application_Simulation_Colab.ipynb`

The third notebook launches the interactive Gradio application from Colab.

---

## Optional multilingual embeddings

The default project works without an external AI API.

For multilingual sentence embeddings:

```bash
pip install -r requirements_embeddings.txt
```

The semantic search layer automatically falls back to TF-IDF when Sentence Transformers is unavailable.

---


## 🤖 Local LLM + Agent mode

The project now includes an optional **real local LLM layer** without a paid API key.

```text
User
  ↓
Local LLM (Ollama or Transformers)
  ↓
Structured intent
  ↓
SmartTrip Agent
  ├── SQLite / SQL
  ├── semantic search
  ├── budget optimization
  └── itinerary generation
  ↓
Local LLM
  ↓
Natural-language answer
```

### Test immediately without downloading a model

The `mock` backend validates the complete orchestration:

```bash
python app/llm_agent.py
```

or run:

```bash
streamlit run app/llm_app.py
```

### Use a real local LLM with Transformers

```bash
pip install -r requirements_llm_local.txt
```

Then set:

```bash
SMARTTRIP_USE_TRANSFORMERS=1
LOCAL_HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

### Use Ollama locally

Configure:

```bash
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b
```

No paid API key is required. Model downloads and local compute are still required.

### Colab

Open:

`notebooks/Cameroon_SmartTrip_LLM_Local_Agent_Colab.ipynb`

The notebook first tests the architecture with the mock backend, then provides a cell for a real local Transformers model.

---

## Simulation

The project includes two simulation modes.

### Traveler profile simulation

Synthetic traveler profiles vary:

- origin;
- budget;
- number of travelers;
- trip duration;
- preferences;
- selected activities.

The tourism dataset itself remains source-based and is **not simulated**.

### Budget stress test

The same traveler profile is evaluated across several budgets to observe:

- feasibility thresholds;
- hotel changes;
- transport-class changes;
- activity removal;
- budget remaining.

Precomputed examples are available in `simulation_results/`.

---

## Data policy

This project follows one important rule:

> **Unknown tourism data is never invented.**

Rows keep provenance fields such as:

- `source_url`
- `source_type`
- `verified_on`
- `data_status`

Public prices may change and must be confirmed with the provider before any booking.

---

## Project status

**Functional prototype / pre-MVP.**

What it does:
- recommends and simulates travel plans.

What it does not yet do:
- live inventory checks;
- payments;
- guaranteed reservations;
- production-grade provider integrations.

---

## Roadmap

Next steps include:

- Kribi geocoding improvements;
- more destinations across Cameroon;
- provider WhatsApp/contact actions;
- live fare and availability verification;
- user accounts and history;
- partner dashboard;
- deployment as a public MVP.

---

## Tech stack

`Python` · `Pandas` · `SQLite` · `Scikit-learn` · `Streamlit` · `Gradio` · `Matplotlib` · `Jupyter/Colab`

Optional:

`Sentence Transformers`

---

## Disclaimer

Cameroon SmartTrip is an experimental travel-planning prototype. Prices and schedules are date-stamped snapshots and may change. Availability and booking must be confirmed directly with the relevant provider.

---

## License

MIT License.
