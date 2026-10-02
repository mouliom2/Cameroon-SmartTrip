# Architecture V3

## 1. NLP Parser
Extraction déterministe de contraintes en français.

## 2. Recherche sémantique
Sentence-Transformers si disponible, sinon TF-IDF.

## 3. Planner Agent
Explore hôtels × classes de transport × sous-ensembles d'activités.

## 4. Budget
Vérifie la faisabilité et retourne la meilleure combinaison connue.

## 5. Itinéraire
Génère un programme jour par jour à partir des sites réels intégrés.

## 6. Garde-fous
- pas de paiement ;
- pas de disponibilité inventée ;
- prix datés ;
- sources visibles.
