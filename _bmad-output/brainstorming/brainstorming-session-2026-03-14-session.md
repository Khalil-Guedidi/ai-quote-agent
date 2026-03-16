---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Agent IA autonome v2 pour le traitement des demandes de devis (mail → ERP), en Python'
session_goals: 'Explorer les architectures agent, patterns de raisonnement autonome, stratégies de décision, et leviers pour une v2 surboostée vs pipeline LLM initial'
selected_approach: 'ai-recommended'
techniques_used: ['Question Storming', 'First Principles Thinking', 'Morphological Analysis']
techniques_completed: ['Question Storming', 'First Principles Thinking', 'Morphological Analysis']
ideas_generated: ['zero-preprocessing', 'adaptive-reasoning', '3-layer-memory', 'emergent-graph', 'multi-proposals', 'erp-abstraction', 'self-hosted-first', 'llm-agnostic', 'confidence-tiers', 'proposability-filter']
questions_generated: 130
session_status: 'completed'
session_active: false
workflow_completed: true
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Khalil
**Date:** 2026-03-14

## Session Overview

**Topic:** Agent IA autonome v2 pour le traitement des demandes de devis (mail → ERP), en Python
**Goals:** Explorer les architectures agent, patterns de raisonnement autonome, stratégies de décision, et identifier les leviers pour créer une v2 véritablement surboostée par rapport au pipeline LLM initial (microservices, prompting dynamique, fuzzy search Solr, SAP)

### Session Setup

_Session initiée par Khalil, AI/LLM Integration Engineer avec expérience directe sur une v1 en production chez ArcelorMittal. La v1 utilisait un pipeline LLM avec architecture microservices, prompting dynamique, recherche fuzzy Solr, et intégration SAP. L'objectif de la v2 est de passer d'un pipeline à un agent véritablement autonome, en Python._

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Agent IA autonome v2 pour le traitement des demandes de devis, avec focus sur architecture agent, raisonnement autonome, et stratégies de décision.

**Recommended Techniques:**

- **Question Storming (deep):** Cartographier l'espace-problème de l'agent autonome en générant uniquement des questions — déconstruire les hypothèses héritées de la v1.
- **First Principles Thinking (creative):** Repartir des vérités fondamentales pour définir ce que doit être un agent autonome de traitement de devis, au-delà du paradigme pipeline.
- **Morphological Analysis (deep):** Explorer systématiquement toutes les combinaisons de paramètres architecturaux pour identifier les designs les plus prometteurs.

**AI Rationale:** Séquence conçue pour d'abord déconstruire (questions), puis reconstruire depuis la base (principes), puis explorer systématiquement (morphologie). Chaque phase nourrit la suivante.

## Technique Execution: Question Storming (Phase 1 — COMPLETE)

**Status:** Terminé
**Questions générées:** ~130+ sur 19 axes orthogonaux

### Axe 1 — Auto-évaluation & feedback loop (~8 questions)
- Qui définit ce qu'est un "bon" devis ? L'agent, le commercial, le client, l'ERP ?
- Est-ce que "bon" veut dire "techniquement correct" ou "commercialement pertinent" — ou les deux ?
- L'agent peut-il comparer son brouillon à des devis passés acceptés par le client ?
- Faut-il un second regard IA (un "reviewer agent") qui valide le travail du premier ?
- Comment capturer le feedback du commercial qui corrige le brouillon dans SAP — et comment ce feedback revient-il à l'agent ?
- Peut-on mesurer un "score de confiance" du devis avant qu'un humain le voie ?
- Comment l'agent sait si le devis est bien généré ou pas ?
- S'il est pas bon, qu'est-ce qui a échoué ? Comment éviter que ça se reproduise ?

### Axe 2 — Incertitude & escalade (~5 questions)
- À partir de quel seuil d'incertitude l'agent doit-il escalader à un humain ?
- Comment l'agent exprime-t-il son doute — "je suis sûr à 40% que c'est le bon produit" ?
- Peut-il poser des questions au commercial par mail ou chat avant de finaliser ?
- Doit-il proposer plusieurs options plutôt qu'une seule ?
- Qui reçoit l'escalade — et comment cette personne interagit-elle avec l'agent ?

### Axe 3 — Scope & limites (~4 questions)
- Comment l'agent détecte-t-il qu'un devis dépasse ses capacités ?
- Le scope doit-il être explicitement défini, ou l'agent apprend-il ses propres limites ?
- Un devis "hors scope" aujourd'hui peut-il devenir "dans le scope" demain ?
- Peut-il traiter partiellement un devis complexe et déléguer la partie difficile ?

### Axe 4 — Amélioration continue (~4 questions)
- L'agent peut-il apprendre de chaque devis sans réentraînement du modèle ?
- Faut-il une mémoire long-terme des cas difficiles ?
- Comment distinguer une erreur systémique d'une erreur ponctuelle ?
- Peut-on créer un pipeline de "replay" pour vérifier la progression ?

### Axe 5 — Architecture mono vs multi-agent (~7 questions)
- Un seul agent ou plusieurs qui tournent en même temps ?
- Si plusieurs agents, qui orchestre ? Un méta-agent ? Un système de règles ?
- Un agent spécialisé par étape serait-il plus fiable qu'un généraliste ?
- Si un agent spécialisé échoue, les autres peuvent-ils compenser ?
- Les agents peuvent-ils se contredire ? Comment trancher ?
- Un agent "superviseur" qui ne fait que vérifier, gaspillage ou assurance qualité ?
- L'agent peut-il déléguer dynamiquement selon la complexité ?
- Comment les agents partagent-ils le contexte sans perte d'information ?

### Axe 6 — Scaling & performance (~7 questions)
- Comment scaler un tel système ?
- 10 devis/jour vs 1000 — même système ou architecture différente ?
- Comment gérer les pics (lundi matin, 200 mails) ?
- Faut-il un système de priorité (gros client vs petit) ?
- Le coût API LLM scale linéairement — à quel volume ça devient prohibitif ?
- Peut-on cacher/mémoriser les résultats pour des demandes similaires ?
- Faut-il des modèles légers pour les cas simples et réserver les gros pour les cas complexes ?

### Axe 7 — Ambiguïté, matching produit & flou client (~8 questions)
- Comment l'agent gère une base produit trop grosse ?
- Comment l'agent décide que le client n'est pas assez clair ?
- Si plusieurs produits sont similaires, comment choisir ?
- "500 barres d'acier" — quelle nuance, dimension, traitement de surface ?
- Si le client utilise ses propres références produit, comment mapper ?
- Le client écrit avec fautes, abréviations, jargon — comment normaliser ?
- Si le client mélange plusieurs demandes dans un mail ?
- Les clients récurrents — l'agent devrait-il connaître leurs habitudes ?
- La base produit change — comment rester à jour sans intervention manuelle ?

### Axe 8 — Sécurité & attaques (~9 questions)
- Comment éviter le prompt injection ?
- Un client peut-il injecter des instructions dans son mail ?
- Comment séparer données (mail) et instructions (prompt) de manière étanche ?
- Si l'agent a accès en écriture à l'ERP, quel est le pire scénario ?
- Faut-il un principe de moindre privilège (brouillons uniquement) ?
- Comment détecter une tentative d'attaque vs un mail légitime mal formulé ?
- L'agent peut-il être manipulé via des pièces jointes (PDF texte caché, image texte invisible) ?
- Faut-il un sandbox — proposition sans écriture directe ?
- Qui audite les actions ? Log immutable de chaque décision ?
- Comment empêcher un employé malveillant d'utiliser l'agent comme vecteur d'attaque ?

### Axe 9 — Confiance & adoption (~8 questions)
- Le commercial faisait-il confiance à la v1 ? Qu'est-ce qui manquait ?
- L'agent doit-il expliquer ses décisions ? À quel niveau de détail ?
- Si l'agent se trompe 3 fois de suite, comment reconstruire la confiance ?
- Faut-il un "mode transparent" avec raisonnement visible en temps réel ?
- Comment mesurer la confiance des utilisateurs ?
- L'agent doit-il avoir une personnalité ? Un ton humble quand il doute ?
- Comment gérer la résistance au changement ?
- Faut-il une phase de cohabitation agent/humain en parallèle ?

### Axe 10 — Portabilité ERP (~6 questions)
- Et si l'entreprise change d'ERP ?
- L'agent doit-il être agnostique ERP dès le départ ?
- Faut-il une couche d'abstraction — un "connecteur" interchangeable ?
- SAP, Oracle, Odoo, Dynamics — structures assez similaires pour un même agent ?
- Comment gérer les champs spécifiques à un ERP inexistants dans un autre ?
- L'agent pourrait-il gérer plusieurs ERP simultanément (multi-sites) ?

### Axe 11 — Données, mémoire & RGPD (~7 questions)
- Mails clients = données personnelles — RGPD, combien de temps stocker ?
- Stocker les mails originaux ou juste les données extraites ?
- Droit à l'oubli — comment ça impacte la mémoire de l'agent ?
- Données envoyées au LLM via API — où transitent-elles ?
- LLM on-premise pour données sensibles ou API cloud avec garanties ?
- Comment versionner la connaissance de l'agent ? Rollback = perte d'apprentissage ?
- Prix confidentiels — jamais dans les logs ou prompts ?

### Axe 12 — Business model (~8 questions)
- Outil interne pour UN client ou produit SaaS pour le marché ?
- Qui est l'acheteur ? Directeur commercial, DSI, DAF ?
- Argument de vente — gain de temps, réduction d'erreurs, scalabilité ?
- Combien coûte un devis mal traité aujourd'hui ? ROI mesurable ?
- Concurrents existants ? Qu'est-ce qui différencie ?
- Modèle freemium ?
- Pricing au devis, à l'utilisateur, ou au forfait ?
- Comment démontrer la valeur en 5 minutes ?

### Axe 13 — Onboarding & cold start (~8 questions)
- Nouveau client — combien de temps avant que l'agent soit opérationnel ?
- Comment ingérer un catalogue de 50 000 références ?
- Et si le catalogue n'est pas propre — doublons, incohérences, données manquantes ?
- Phase de calibration sur des devis historiques ?
- Fonctionner avec un catalogue partiel et s'améliorer au fil de l'eau ?
- Qui configure l'agent côté client ?
- Spécificités métier de chaque client — terminologie, workflows, pricing ?
- Templates par industrie pour accélérer le démarrage ?

### Axe 14 — Edge cases & chaos réel (~9 questions)
- Mail en allemand, chinois, ou mélange de langues ?
- PDF scanné, tordu, avec annotations manuscrites ?
- Excel avec 200 lignes dans un mail — un devis ou plusieurs ?
- "Comme d'habitude" sans précision — l'agent comprend ?
- Nouvelle demande cachée dans un ancien thread mail ?
- Commercial qui forwarde avec "tu peux t'en occuper ?" — qui est le client ?
- 12 pièces jointes dont une seule pertinente ?
- Demande urgente vendredi 23h — traitement différent ?
- Fautes de frappe — "acer inox", "500 T" (tonnes ou unités ?) ?

### Axe 15 — Écosystème technique (~9 questions)
- Quel framework agent ? LangGraph, CrewAI, custom ?
- Message broker (RabbitMQ, Kafka) ou simple polling IMAP ?
- Cloud, on-premise, hybride ?
- Comment versionner les prompts ?
- Comment tester un agent non-déterministe ?
- Mode "replay" pour rejouer des scénarios en dev/staging ?
- CI/CD sur un système dépendant d'un LLM externe ?
- Observabilité — OpenTelemetry, logs structurés, traces de raisonnement ?
- Comment debugger un comportement inattendu ?

### Axe 16 — UX & interfaces (~8 questions)
- Interface commerciale — dashboard, plugin Outlook, bot Teams/Slack ?
- Vue temps réel des devis en cours de traitement ?
- Notification "j'ai traité votre devis, vérifiez le brouillon" ?
- Correction directe depuis l'interface — apprise par l'agent ?
- Tableau de bord manager avec KPIs ?
- "Inbox de doutes" pour les cas incertains ?
- Chat interactif agent-commercial ?
- Validation mobile en déplacement ?

### Axe 17 — Temporalité & cycle de vie (~7 questions)
- Durée de validité du devis — tracker les expirations ?
- Client qui relance 3 semaines plus tard — l'agent fait le lien ?
- Avenants — "même devis mais changez la quantité" ?
- Suivi post-devis — relance client, conversion en commande ?
- Devis récurrents — "même commande que le mois dernier" ?
- Patterns saisonniers — "ce client commande toujours en mars" ?
- Produit en rupture de stock — proposer une alternative ?

### Axe 18 — Éthique & responsabilité (~6 questions)
- Erreur qui coûte 100K€ — qui est responsable ?
- Discrimination involontaire — traiter plus vite les gros clients ?
- Informer le client que son devis est traité par une IA ? Obligation légale ?
- L'agent peut-il prendre des décisions de pricing ?
- Comment éviter les hallucinations de produits inexistants ?
- Demande illégale ou sanctionnée (export controls) — que fait l'agent ?

### Axe 19 — Compétition & marché (~5 questions)
- SAP va-t-il intégrer cette fonctionnalité nativement ?
- Les ERP cloud ajoutent de l'IA — comment rester pertinent ?
- Spécialisation devis ou approche agent généraliste ?
- Se positionner comme "middleware IA" entre mail et ERP ?
- Les intégrateurs SAP comme partenaires plutôt que concurrents ?

---

## Technique Execution: First Principles Thinking (Phase 2 — COMPLETE)

**Status:** Terminé
**Principes fondamentaux identifiés:** 13

### Hypothèses de la v1 déconstruites

**Architecture réelle de la v1 :**
- Flow : Email Reception → Email Cleaning → Structured Extraction → Product Matching → Stock Verification → Quote Generation → Sales Rep Notification
- Chaque étape = microservice Node.js isolé, communication asynchrone via RabbitMQ
- Déclencheur semi-manuel : le commercial forwarde vers une boîte générique
- Le LLM faisait le cleaning, l'extraction ET le matching produit
- Solr servait de pré-filtre pour réduire les candidats avant que le LLM choisisse (sinon trop d'erreurs)
- Le nettoyage de la base produit (synonymes, renommage, blacklist, tri) était nécessaire pour que Solr filtre correctement
- La précision s'est construite sur des semaines d'affinage : ajustement Solr + accumulation de règles métier hardcodées dans les microservices

**Frustrations majeures identifiées :**
1. Temps massif passé à nettoyer/préparer la base produit pour Solr
2. Semaines d'affinage avant un bon taux de précision
3. Accumulation excessive de règles métier hardcodées — système de plus en plus rigide et fragile

### Les 13 Vérités Fondamentales pour la v2

| # | Vérité fondamentale | Ce que ça élimine de la v1 |
|---|---------------------|---------------------------|
| F1 | Le traitement est un raisonnement avec boucles et retours, pas une séquence linéaire | Chaîne séquentielle de 7 étapes |
| F2 | L'agent a besoin d'une vision globale, pas de fragments isolés | Découpage en microservices isolés |
| F3 | Le LLM a besoin d'aide pour réduire les candidats — mais sémantique, pas manuelle | Nettoyage manuel de la base produit |
| F4 | Le pré-filtrage doit comprendre le sens — embeddings > fuzzy search | Solr + synonymes + renommage |
| F5 | L'agent gère son incertitude — doute, escalade, alternatives | Flow unidirectionnel fire-and-forget |
| F6 | Le déclencheur est l'intention du client, pas un forward manuel | Trigger semi-manuel |
| F7 | La connaissance métier est dynamique et apprise, pas codée en tables statiques | Tables de synonymes, blacklists |
| F8 | La base produit est un input brut — c'est la représentation qui doit être intelligente | Tout le preprocessing de la base |
| F9 | L'agent apprend de ses erreurs sans intervention développeur | Hotfixes manuels à chaque erreur |
| F10 | Le système doit être utile dès le jour 1, même imprécis | Semaines d'affinage avant valeur |
| F11 | La logique métier vit dans le contexte de l'agent, pas dans le code | Règles métier hardcodées dans les services |
| F12 | L'agent doit généraliser, pas accumuler des cas particuliers | Accumulation de règles spécifiques |
| F13 | Chaque décision est traçable et diagnosticable | Impossible de savoir où l'erreur se produit |

---

## Technique Execution: Morphological Analysis (Phase 3 — COMPLETE)

**Status:** Terminé
**Paramètres explorés:** 7
**Décisions architecturales prises:** 7

### Contexte clé découvert pendant l'analyse

- **Vision produit** : Ce n'est pas un projet interne — c'est un produit SaaS multi-client
- **Chaque décision doit répondre à** : "Est-ce que ça scale à N clients sans recoder ?"
- **Modèle comportemental** : L'agent simule un très bon commercial, pas un pipeline technique
- **Connaissance tacite** : Les sous-entendus, produits par défaut, jargon client sont de la connaissance implicite à 3 niveaux (industrie/entreprise/client)
- **Base produit polluée** : Produits custom à usage unique mélangés aux produits standards — nécessite un filtre de proposabilité
- **V1 forçait toujours une réponse** — aucune gestion d'incertitude, le commercial corrigeait systématiquement

### Grille Morphologique — 7 Paramètres

| Paramètre | Choix retenu | Justification |
|---|---|---|
| **A. Pattern agent** | Multi-agent contextuel | Vision produit multi-client — les agents sont recontextualisés par client, pas recodés |
| **B. Raisonnement** | Adaptatif "bon commercial" | Classification initiale (simple/ambigu/complexe/hors scope) → pattern de raisonnement approprié + mémoire 3 couches |
| **C. Recherche produit** | Hybride (vector + keyword) + filtre proposabilité + graphe émergent | Vector pour le sens, keyword pour les références exactes, filtre pour exclure les produits custom/obsolètes, graphe construit par observation passive |
| **D. Mémoire** | Few-shot dynamique + long-term memory profil + graphe par observation | Exemples de devis réussis injectés dynamiquement, profil client persistant, patterns détectés par process séparé avec seuil de confirmation |
| **E. Incertitude** | Système à paliers configurable | Haute confiance (>85%) → brouillon ERP avec review. Moyenne (50-85%) → multi-propositions au commercial. Basse (<50%) → escalade avec contexte enrichi. Seuils configurables par client |
| **F. Intégration ERP** | Couche d'abstraction agnostique + adaptateurs | L'agent raisonne en "devis générique", un adaptateur traduit vers SAP/Odoo/Dynamics/Oracle. RPA en fallback pour ERP legacy sans API |
| **G. Infrastructure** | Monolithe modulaire Python + LangGraph | Un seul service par instance, modulaire en interne, LangGraph comme colonne vertébrale agent, scale horizontal par instance |

### Architecture de raisonnement "Bon commercial"

```
Mail entrant
    ↓
[Classification] → Simple / Ambigu / Complexe / Hors scope
    ↓                ↓           ↓            ↓
  Exécution      Enquête    Décomposition   Redirection
  directe        (ReAct)    (Plan+Execute)  rapide
    ↓                ↓           ↓
         [Self-review avant envoi à l'ERP]
```

### Architecture mémoire 3 couches + émergente

| Couche | Contenu | Mécanisme technique |
|---|---|---|
| Industrie | Conventions, normes, défauts métier | Base de connaissances RAG partagée par secteur |
| Entreprise | Catalogue, règles internes, workflows | Contexte configurable par client |
| Client (exemples) | Devis passés similaires réussis | Few-shot dynamique depuis historique |
| Client (profil) | Habitudes, préférences, particularités | Long-term memory persistante |
| Émergente | Relations produit, patterns détectés | Graphe construit par observation passive (seuil + validation) |

### Architecture recherche produit 3 étages

```
Étage 1 — Filtre de proposabilité (AVANT la recherche)
    → Exclut custom/obsolètes/hors stock, configurable par client
        ↓
Étage 2 — Recherche hybride (vector + keyword)
    → Sur base filtrée, enrichie par mémoire client
        ↓
Étage 3 — Raisonnement final par l'agent
    → 5-10 candidats, choix avec contexte complet ou multi-propositions
```

### Système de confiance à paliers

```
Score confiance calculé
    ↓
Haute (>85%) → Agent reviewer vérifie → Brouillon ERP
Moyenne (50-85%) → Multi-propositions au commercial (valide en 1 clic)
Basse (<50%) → Escalade avec contexte enrichi au commercial
    ↓
Chaque correction/validation → alimente le few-shot dynamique
```

### Intégration ERP agnostique

```
Agent → Devis format universel → Adaptateur ERP → Brouillon ERP
                                    ├── SAP
                                    ├── Odoo
                                    ├── Dynamics
                                    ├── Oracle
                                    └── RPA fallback (legacy)
```

## Idea Organization and Prioritization

### Thematic Organization

**Theme 1: Intelligence produit & matching**
- Zéro preprocessing de la base produit — la couche de représentation est intelligente, pas la base
- Recherche hybride (vector + keyword) remplace Solr + nettoyage manuel
- Filtre de proposabilité élimine les custom/obsolètes avant la recherche
- Graphe émergent construit par observation passive

**Theme 2: Raisonnement & autonomie**
- Classification initiale (simple/ambigu/complexe/hors scope) pour router le raisonnement
- Pattern adaptatif "bon commercial" : exécution directe, enquête ReAct, décomposition, redirection
- Self-review avant chaque envoi à l'ERP
- Système de confiance à paliers configurable par client

**Theme 3: Mémoire & apprentissage**
- Mémoire 3 couches : industrie / entreprise / client
- Connaissance tacite capturée : sous-entendus, produits par défaut, habitudes
- Few-shot dynamique depuis devis réussis
- Apprentissage par observation passive avec seuil de confirmation

**Theme 4: Architecture produit multi-client**
- Multi-agent contextuel — recontextualiser, pas recoder
- Couche d'abstraction ERP agnostique + adaptateurs
- Monolithe modulaire Python + LangGraph
- Self-hosted first — données sensibles ne quittent jamais le client
- LLM-agnostique — API cloud ou modèle local au choix du client

**Theme 5: Sécurité, confiance & adoption**
- Principe de moindre privilège, traçabilité complète
- Onboarding progressif : observation → assisté → autonome
- Multi-propositions quand l'agent n'est pas sûr — utile même imprécis

**Breakthrough Concept: Graphe émergent**
- Moat technique — impossible à reproduire sans le volume de données
- Plus l'agent traite de devis, plus il est précis
- Construit par observation passive, validé avant activation
- Local par client (privacy), cross-client uniquement en opt-in

### Prioritization Results

**Top 3 High-Impact Ideas:**
1. **Zéro preprocessing de la base produit** — argument de vente killer, élimine la frustration #1 de la v1
2. **Pattern adaptatif "bon commercial"** — ce qui fait que c'est un agent, pas un pipeline
3. **Mémoire 3 couches** — ce qui rend l'agent meilleur à chaque devis

**Quick Win:** Matching avec multi-propositions — l'agent propose 3 produits, le commercial valide en 1 clic. Utile même quand l'agent est imprécis.

**Most Innovative:** Graphe émergent — avantage concurrentiel qui se creuse avec le temps, impossible à rattraper par un concurrent.

### Action Plans

**Priorité 1: Zéro preprocessing base produit**
- Étape 1: Générer un catalogue synthétique réaliste (~5000 produits avec bruit, doublons, customs)
- Étape 2: Prototyper l'indexation vectorielle sur ce catalogue brut
- Étape 3: Benchmarker vector vs hybrid search sur des requêtes simulées
- Étape 4: Implémenter le filtre de proposabilité
- Indicateur: Taux de matching satisfaisant sans aucun nettoyage de base
- Risque: Embeddings génériques insuffisants pour jargon métier spécifique

**Priorité 2: Pattern adaptatif "bon commercial"**
- Étape 1: Définir le classifieur initial (critères simple/ambigu/complexe/hors scope)
- Étape 2: Implémenter le cas "simple" d'abord (client clair, produit évident)
- Étape 3: Ajouter le cas "ambigu" avec boucle ReAct
- Étape 4: Cas complexe (décomposition) et hors scope (redirection)
- Indicateur: Classifieur route correctement 90%+ des mails
- Risque: Frontière floue entre simple et ambigu — itérer sur les seuils

**Priorité 3: Mémoire 3 couches**
- Étape 1: Couche entreprise (catalogue, config client) — la plus structurée
- Étape 2: Couche client avec few-shot dynamique (devis validés comme exemples)
- Étape 3: Couche industrie (nécessite données multi-clients)
- Étape 4: Feedback loop — correction commercial → stockée → utilisable comme few-shot
- Indicateur: Précision mesurablment meilleure sur le 50ème devis vs le 1er
- Risque: Qualité des corrections commerciales

**Données de développement:**
- Catalogue synthétique réaliste généré par LLM pour le dev et les tests
- Vrai catalogue dès qu'un early-adopter est trouvé

**Positionnement produit corrigé:**
- Self-hosted first (données sensibles restent chez le client)
- LLM-agnostique (API cloud ou modèle local au choix)
- Graphe émergent local par client (privacy)
- Potentiellement un tier SaaS pour petits clients

**Roadmap graphe émergent:**
1. V2.0: Pas de graphe — le matching fonctionne sans
2. V2.1: Logging structuré de chaque matching réussi
3. V2.2: Détection de patterns sur les logs (process batch)
4. V2.3: Relations activées comme enrichissement du contexte agent
5. V2.4: Graphe cross-client par industrie en opt-in (anonymisé)

## Session Summary and Insights

**Key Achievements:**
- 130+ questions sur 19 axes — cartographie exhaustive de l'espace-problème
- 13 vérités fondamentales extraites de la déconstruction de la v1
- 7 décisions architecturales structurantes pour le produit
- Vision produit clarifiée : self-hosted, multi-client, LLM-agnostique
- 3 priorités d'implémentation avec plans d'action concrets
- 1 concept innovant (graphe émergent) identifié comme moat technique

**Session Reflections:**
- La frustration #1 de la v1 (nettoyage base produit) est devenue l'argument de vente #1 de la v2
- Le passage de "pipeline" à "agent" ne se résume pas à un changement technique — c'est un changement de paradigme : l'agent raisonne, doute et apprend
- Le modèle du "bon commercial" est le meilleur guide de conception — chaque décision architecturale peut être validée par "est-ce qu'un bon commercial ferait ça ?"
- Le choix self-hosted est cohérent avec le marché cible (entreprises industrielles, données sensibles)

**Creative Facilitation Narrative:**
Session de brainstorming en 2 jours avec Khalil, AI/LLM Integration Engineer. Le point de départ était une v1 fonctionnelle mais frustrante (pipeline LLM + microservices Node.js + Solr chez ArcelorMittal). Les moments clés : la déconstruction de l'hypothèse "base produit propre obligatoire" qui a révélé que le problème était la représentation, pas les données ; la correction de Khalil sur le rôle réel de Solr (pré-filtre pour le LLM, pas le matcher lui-même) qui a affiné l'analyse ; et le recadrage sur le choix agent+outils vs multi-agent qui a poussé à clarifier la vision produit vs projet. La session a évolué d'une exploration technique vers une vision produit complète.
