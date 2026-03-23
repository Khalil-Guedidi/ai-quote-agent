# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.4 : Fondation terminée : 8 stories, 68 tests, zéro étape manuelle
- **Phase :** Fondation (Epic 1)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Screenshot métriques
- **Description :** Screenshot tableau métriques (tests, couverture, docker compose up)
- **Dimensions :** 1200x627px
- **Outil suggéré :** Capture d'écran annotée
- **Notes :** Annoter avec flèches les chiffres clés : 68 tests, 5 adaptateurs, docker compose up en une commande. Montrer le terminal avec les tests qui passent en vert. Compréhensible sans lire le texte.

---

## Post LinkedIn

Mon prototype faisait 96.2% de précision. Il avait aussi zéro test, zéro processus de déploiement, et zéro chance de survivre en production.

Le fossé dont personne ne parle. Une démo qui marche et un système de production, ce sont deux choses complètement différentes. Le prototype prouvait que l'idée fonctionnait. Mais "ça marche sur mon laptop" ne veut pas dire "prêt pour l'infrastructure d'un client".

J'ai passé plusieurs semaines à tout reconstruire. Pas la partie IA. Tout le reste. Un système de configuration propre. Une base de données avec des migrations. Des health checks pour chaque service externe. Des adaptateurs qui permettent de changer n'importe quelle intégration sans toucher au reste du code. Un déploiement Docker pour qu'un client lance une seule commande au lieu de suivre un guide de 20 étapes.

8 stories. 5 adaptateurs. 68 tests automatisés là où il y en avait zéro.

Rien de spectaculaire à montrer. Pas de démo impressionnante. Juste la fondation invisible qui rend tout le reste fiable.

Quelle proportion de vos projets représente le travail invisible que personne ne voit jamais ?

---

## Hashtags

#IA #PME #BuildInPublic #AI #IndustrieB2B

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

Post #4 de la série, dernier post de la phase Fondation (Epic 1). T.3 montrait le défi des données sales. Ce post ferme la phase : l'infrastructure invisible est en place. La semaine prochaine, la série entre dans la phase Pipeline Email (Epic 2) : le jargon industriel français.
