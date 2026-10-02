# Architecture LLM local + Agent

## Pipeline

```text
Utilisateur
   ↓
LLM local
   ↓
Extraction structurée
   ↓
Agent SmartTrip
   ├── SQLite / SQL
   ├── recherche sémantique
   ├── calculs
   └── optimisation du budget
   ↓
Plan structuré
   ↓
LLM local
   ↓
Réponse naturelle
```

## Backends

### Ollama
- gratuit ;
- local ;
- aucune clé API payante ;
- nécessite Ollama et un modèle téléchargé.

### Transformers / Hugging Face
- gratuit ;
- local dans Colab ou sur ordinateur ;
- aucun token API payant ;
- le premier téléchargement des poids nécessite Internet.

### Mock
- sert aux tests automatiques ;
- ne prétend pas être un vrai LLM ;
- permet de valider toute l'orchestration sans téléchargement.

## Fallback

Le projet original reste disponible. Si aucun LLM local n'est disponible,
SmartTrip peut continuer à utiliser son parseur NLP déterministe.
