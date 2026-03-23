# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.2 : Choix de stack : pourquoi Python et LangGraph pour un agent de devis
- **Phase :** Fondation (Epic 1)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Schéma architecture
- **Description :** Diagramme architecture production : 5 adaptateurs (DB, LLM, ERP, Email, Notifs) + stack technique
- **Dimensions :** 1200x627px
- **Outil suggéré :** Excalidraw ou Mermaid
- **Notes :** Montrer les 5 adaptateurs comme des blocs modulaires connectés au coeur de l'agent. Chaque bloc porte son nom et sa techno (PostgreSQL, Claude, Odoo, IMAP, Teams). Compréhensible sans lire le texte.

---

## Post LinkedIn

Mon prototype n8n faisait 96% de précision. Alors je l'ai jeté et j'ai tout recommencé en Python.

n8n était parfait pour valider l'idée en quelques jours. Workflows visuels, itération rapide, un agent de devis fonctionnel très vite. Mais quand j'ai commencé à penser production, les limites sont apparues. Pas de tests, pas de gestion d'erreurs propre, pas de contrôle sur le raisonnement de l'agent.

J'ai tout reconstruit. Python avec LangGraph pour définir exactement comment l'agent réfléchit, étape par étape. Une seule base PostgreSQL pour les données et la recherche vectorielle, au lieu de jongler avec deux bases. Et des tests automatisés dès le premier jour.

Deux stories plus tard : 21 tests automatisés et une structure de projet propre. Le prototype avait zéro test.

Le prototypage et la production, ce sont deux métiers différents. L'un récompense la vitesse, l'autre la fiabilité.

À quel moment vous décidez d'arrêter d'itérer sur un truc qui marche "à peu près" et de repartir sur de bonnes bases ?

---

## Hashtags

#IA #TransformationDigitale #BuildInPublic #AI #PME

---

## Checklist de formatage

- [x] Longueur totale : 120-200 mots
- [x] Rédigé en français (termes techniques anglais en ligne seulement)
- [x] Asset visuel prêt (carousel, screenshot, schéma ou démo)
- [x] Le visuel est compréhensible sans lire le texte
- [x] Pas de noms de clients ni d'info confidentielle
- [x] Toutes les données viennent du code et des métriques de ce repo
- [x] Expérience professionnelle cadrée comme expertise domaine, pas travail client
- [x] Au moins un chiffre ou une métrique concrète
- [x] Finit par une question pour audience non technique
- [x] Ton humain, familier, expert-qui-simplifie
- [x] Pas de tirets longs, pas de "C'est X, pas Y"
- [x] Pas de buzzwords corporate
- [x] Hashtags (4-5 max) : mix français + anglais, inclut #BuildInPublic

---

## Note de continuité

Post #2 de la série. T.1 annonçait les résultats du prototype et la reconstruction pour la production. Ce post explique pourquoi le changement de stack : de n8n à Python/LangGraph. La semaine prochaine : le vrai problème des données sales en B2B industriel.
