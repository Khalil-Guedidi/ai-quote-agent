# Page Projet Contra

---

## Version française (principale)

### Titre du projet

Agent IA de devis B2B industriel : Build in Public

### Description du projet

Un système IA complet qui automatise la génération de devis industriels B2B : de la réception d'email à la recherche de produits, jusqu'à la création de brouillons de devis dans un ERP.

C'est un projet solo Build in Public, documenté du prototype à la production. Chaque décision d'architecture, chaque résultat de benchmark et chaque leçon apprise est partagée publiquement.

### Vue d'ensemble du prototype

#### Architecture

- **Orchestration :** n8n (prototype), Python/LangGraph (production)
- **ERP :** Odoo 18 Community : catalogue produits, données clients, gestion des devis
- **Base vectorielle :** PostgreSQL + pgvector : recherche sémantique sur embeddings produits
- **Embeddings :** OpenAI text-embedding-3-small
- **LLM :** Claude (extraction structurée + matching produits + raisonnement devis)
- **Pipeline :** Email, extraction données structurées, recherche hybride, matching produits, brouillon devis

#### Ce qui rend le projet intéressant

- **Complexité domaine :** Les catalogues B2B industriels ont des noms incohérents, du jargon français, des abréviations et des variations d'unités. La recherche par mots-clés seule échoue. La recherche sémantique seule hallucine. La recherche hybride avec reranking adapté au domaine fonctionne.
- **Contraintes réelles :** Intégration ERP, parsing d'emails, demandes de devis multi-lignes. Ce n'est pas une démo, c'est conçu pour la production.

#### Résultats

| Métrique | Résultat |
|----------|----------|
| Précision recherche hybride (Hit@5) | 96.2% |
| Latence bout en bout | 2.9s en moyenne |
| Couverture scénarios | 3/3 (simple, multi-lignes, ambigu) |
| Tests automatisés | 781 (unité) + 28 (E2E) |
| Produits testés | 50 000 |

### Architecture production

Le système de production utilise un **adapter pattern** avec 5 points d'intégration, chacun testable et interchangeable indépendamment :

| Adaptateur | Rôle | Technologie |
|------------|------|-------------|
| Base de données | Catalogue produits, devis, audit trail | PostgreSQL + pgvector, SQLAlchemy async, migrations Alembic |
| Fournisseur LLM | Extraction structurée, raisonnement, matching | API compatible OpenAI avec routage de modèle |
| ERP | Catalogue produits, données clients, création devis | Odoo XML-RPC avec masquage identifiants |
| Email | Réception demandes de devis | IMAP avec parsing structuré |
| Notification | Alertes équipe commerciale | Microsoft Teams Adaptive Cards avec health check webhook |

### Fonctionnalités clés

- **Routage par confiance :** Le système évalue sa propre confiance et route les demandes à faible confiance vers des humains. Trois niveaux : haute (devis auto), moyenne (propositions multiples), basse (escalade humaine).
- **Conformité export :** Détection automatique d'articles sous contrôle export et d'entités sanctionnées.
- **Pipeline LangGraph :** Agent orchestré avec 14 chemins de routage, raisonnement adaptatif et auto-évaluation avant soumission.

### Stack technique

Python 3.12 | LangGraph | PostgreSQL + pgvector | FastAPI | OpenAI | Claude | Odoo 18 | Docker

### Assets visuels

- Screenshots des notifications Teams (3 niveaux : vert/orange/rouge)
- Capture CLI : commande `process` montrant le pipeline email-vers-devis
- Interface Odoo : brouillons de devis générés par l'IA
- Diagramme architecture : pipeline LangGraph avec 14 chemins et nœuds
- Métriques visuelles : 96.2% précision, 2.9s latence, 781 tests, 50K produits

---

## English version (secondary)

### Project Title

AI-Powered B2B Quoting Agent: Building in Public

### Project Description

An end-to-end AI system that automates B2B industrial quote generation: from email reception to product matching to draft quote creation in an ERP.

This is a solo build-in-public project, documented from prototype to production. Every architectural decision, benchmark result, and lesson learned is shared publicly.

### Prototype Results

| Metric | Result |
|--------|--------|
| Hybrid search accuracy (Hit@5) | 96.2% |
| End-to-end latency | 2.9s average |
| Scenario coverage | 3/3 (simple, multi-line, ambiguous) |
| Automated tests | 781 (unit) + 28 (E2E) |
| Products tested | 50,000 |

### What Makes It Interesting

- **Domain complexity:** B2B industrial catalogs have inconsistent naming, French jargon, abbreviations, and unit variations. Pure keyword search fails. Pure semantic search hallucinates. Hybrid search with domain-aware reranking works.
- **Real-world constraints:** ERP integration, email parsing, multi-line quote requests. Designed for production use.
- **Confidence-based routing:** The system scores its own confidence and routes low-confidence requests to humans. Building trust by knowing its limits.

### Technology Stack

Python 3.12 | LangGraph | PostgreSQL + pgvector | FastAPI | OpenAI | Claude | Odoo 18 | Docker

### Architecture

```
Email (IMAP) → FastAPI → LangGraph Agent → Quote Draft
                  ↕            ↕
              PostgreSQL    LLM Provider
              + pgvector   (OpenAI-compat)
                  ↕            ↕
             ERP (Odoo)    Notifications
            XML-RPC         (Teams)
```

Each adapter follows the same pattern: abstract interface, concrete implementation, health check endpoint, independent configuration. This allows swapping any integration without touching the rest of the system.

---

## Project Links

- GitHub: {add_repo_url_when_public}
- LinkedIn Series: {add_first_post_url_when_published}

## Page Notes

- Epics 1-5.5 complete. Full production pipeline operational.
- French version is primary. Target audience is Franco-European industrial market.
- Update metrics as project progresses through Epics 6-9.
- Link to LinkedIn posts as they are published.
- Add visual assets (screenshots, diagrams) when available.
