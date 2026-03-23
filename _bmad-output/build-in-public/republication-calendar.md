# Calendrier de republication : Série Build in Public

## Configuration

- **Date de début :** 2026-03-30 (lundi suivant)
- **Cadence :** 1 post par semaine
- **Jour de publication recommandé :** Mardi ou mercredi, 8h-9h CET
- **Durée totale :** ~30 semaines (14 republication + T.15 + Epics 6-9)

## Guide de publication

- **Meilleurs jours :** Mardi, mercredi, jeudi (l'algorithme LinkedIn favorise le milieu de semaine)
- **Meilleure heure :** 8h-9h CET (pic d'activité LinkedIn France, les décideurs scrollent avant les réunions)
- **Algorithme LinkedIn :** Les posts avec carousel/images obtiennent 2-3x plus de reach que le texte seul. Poster le matin maximise la fenêtre d'engagement de la journée.
- **Engagement :** Répondre aux commentaires dans les 2 premières heures (l'algorithme booste les posts avec de l'activité rapide)

## Calendrier

| Semaine | Date pub. | Post | Titre français | Phase | Format visuel | Description asset visuel | Priorité |
|---------|-----------|------|----------------|-------|---------------|--------------------------|----------|
| 1 | 2026-03-31 (mar) | T.1 | Lancement du prototype : voila ce que l'IA fait pour vos devis | Lancement | Screenshot + schéma | Screenshot résultats prototype (96.2% précision, 2.9s latence) + schéma pipeline simplifié email-vers-devis | **Haute** |
| 2 | 2026-04-07 (mar) | T.2 | Choix de stack : pourquoi Python et LangGraph pour un agent de devis | Fondation | Schéma architecture | Diagramme architecture production : 5 adaptateurs (DB, LLM, ERP, Email, Notifs) + stack technique | Moyenne |
| 3 | 2026-04-14 (mar) | T.3 | Le vrai problème des données sales en B2B industriel | Fondation | Carousel avant/après | Carousel 4-5 slides : exemples données sales (abbréviations, jargon, unités) vs données nettoyées | **Haute** |
| 4 | 2026-04-21 (mar) | T.4 | Fondation terminée : 8 stories, 68 tests, zéro étape manuelle | Fondation | Screenshot métriques | Screenshot tableau métriques (tests, couverture, docker compose up) | Moyenne |
| 5 | 2026-04-28 (mar) | T.5 | "Vis M8x40 inox" : quand l'IA doit apprendre le jargon industriel français | Pipeline Email | Carousel parsing | Carousel 5-6 slides : exemples jargon industriel, comment l'IA apprend à les décoder, avant/après matching | **Haute** |
| 6 | 2026-05-05 (mar) | T.6 | Cas limites : quand un email contient 12 produits et 3 langues | Pipeline Email | Screenshot parsing | Screenshot sortie d'extraction structurée : email brut vs données extraites par le LLM | Moyenne |
| 7 | 2026-05-12 (mar) | T.7 | Premier vrai email traité de bout en bout | Pipeline Email | Démo GIF/screenshot | GIF ou screenshot séquence : email reçu, extraction, matching, devis brouillon dans Odoo | Moyenne |
| 8 | 2026-05-19 (mar) | T.8 | Recherche hybride : ni keyword ni sémantique seul ne suffit | Recherche | Schéma flux | Diagramme flux recherche hybride : keyword + sémantique + reranking, avec scores comparatifs | Basse |
| 9 | 2026-05-26 (mar) | T.9 | Reranking LLM : comment l'IA trie les résultats de recherche | Recherche | Carousel technique | Carousel 4 slides : query, résultats bruts, reranking, résultat final avec scores | Basse |
| 10 | 2026-06-02 (mar) | T.10 | Recherche terminée : 50K produits, 96% de précision | Recherche | Screenshot résultats | Screenshot benchmark résultats recherche avec métriques clés | Moyenne |
| 11 | 2026-06-09 (mar) | T.11 | Quand l'IA hésite, il faut le savoir : niveaux de confiance | Intelligence | Carousel niveaux | Carousel 4-5 slides : 3 niveaux de confiance (vert/orange/rouge), exemples concrets, routage décisionnel | **Haute** |
| 12 | 2026-06-16 (mar) | T.12 | Architecture mémoire : comment l'agent apprend de chaque devis | Intelligence | Schéma architecture | Diagramme mémoire : knowledge base industrie, contexte client, historique feedback | Moyenne |
| 13 | 2026-06-23 (mar) | T.13 | Intelligence terminée : raisonnement adaptatif et auto-évaluation | Intelligence | Screenshot pipeline | Screenshot pipeline LangGraph complet avec 14 chemins et métriques | Moyenne |
| 14 | 2026-06-30 (mar) | T.14 | L'automatisation totale est un piège : la collaboration humain-IA | Boucle complète | Carousel récap | Carousel 5-6 slides : pourquoi 100% auto ne marche pas, le modèle hybride, les 3 niveaux d'intervention humaine, métriques | **Haute** |
| 15 | 2026-07-07 (mar) | T.15 | Le pipeline complet : email, IA, validation humaine, devis envoyé | Boucle complète | Démo vidéo + carousel | Vidéo courte du flux complet email-vers-devis + carousel récap métriques avant/après (prototype vs production) | **Haute** |
| 16 | 2026-07-14 (mar) | T.16 | L'IA qui se souvient de votre industrie : base de connaissances métier | Mémoire (Epic 6) | Schéma architecture | Diagramme 3 couches mémoire : industrie (RAG), entreprise (catalogue/règles), client (historique) | **Haute** |
| 17 | 2026-07-21 (mar) | T.17 | Vos règles métier, comprises par l'IA : contexte entreprise et catalogue | Mémoire (Epic 6) | Carousel processus | Carousel 4-5 slides : comment l'agent intègre les workflows et règles spécifiques d'une entreprise | Moyenne |
| 18 | 2026-07-28 (mar) | T.18 | "Ce client préfère toujours l'inox" : mémoire des préférences clients | Mémoire (Epic 6) | Screenshot avant/après | Screenshot : premier devis vs devis avec mémoire client (personnalisation visible) | **Haute** |
| 19 | 2026-08-04 (mar) | T.19 | Quand le commercial corrige l'IA, elle apprend : boucle de feedback | Mémoire (Epic 6) | Carousel cycle | Carousel 5 slides : correction humaine, capture, apprentissage, amélioration, résultat | Moyenne |
| 20 | 2026-08-11 (mar) | T.20 | Réutiliser les devis validés : l'IA qui capitalise sur votre historique | Mémoire (Epic 6) | Schéma flux | Diagramme : devis validé, extraction patterns, réapplication sur nouvelles demandes similaires | Moyenne |
| 21 | 2026-08-18 (mar) | T.21 | Mémoire terminée : un agent qui s'améliore à chaque devis | Mémoire (Epic 6) | Screenshot métriques | Screenshot évolution métriques avant/après mémoire (précision, temps, pertinence) | Moyenne |
| 22 | 2026-08-25 (mar) | T.22 | Ce que l'IA "pense" quand elle fait votre devis : traçabilité du raisonnement | Observabilité (Epic 7) | Screenshot logs | Screenshot traces de raisonnement structurées : chaque étape visible, chaque décision expliquée | Moyenne |
| 23 | 2026-09-01 (mar) | T.23 | Tableau de bord : voir en un coup d'oeil si l'IA fait bien son travail | Observabilité (Epic 7) | Screenshot dashboard | Screenshot interface dashboard : métriques temps réel, santé des services, alertes | **Haute** |
| 24 | 2026-09-08 (mar) | T.24 | Alertes intelligentes : savoir avant que ça casse | Observabilité (Epic 7) | Screenshot alertes | Screenshot système d'alertes : seuils, notifications, audit trail immutable | Moyenne |
| 25 | 2026-09-15 (mar) | T.25 | Observabilité terminée : un système qu'on peut auditer | Observabilité (Epic 7) | Carousel récap | Carousel 4 slides : dashboard, logs, alertes, audit trail + métriques accessibilité WCAG | Moyenne |
| 26 | 2026-09-22 (mar) | T.26 | Chaque client est différent : configuration des règles métier par entreprise | Configuration (Epic 8) | Carousel exemples | Carousel 4-5 slides : exemples de règles différentes par client (filtres, seuils, workflows) | Moyenne |
| 27 | 2026-09-29 (mar) | T.27 | Configuration terminée : un agent adaptable à chaque entreprise | Configuration (Epic 8) | Schéma configuration | Diagramme : paramétrage par client (filtres proposabilité, seuils confiance, règles métier) | Moyenne |
| 28 | 2026-10-06 (mar) | T.28 | Rejouer 100 scénarios en 5 minutes : tests de régression automatiques | Qualité (Epic 9) | Screenshot tests | Screenshot exécution tests de régression : 100 scénarios rejoués, résultats comparés | Moyenne |
| 29 | 2026-10-13 (mar) | T.29 | Mode cohabitation : l'IA travaille à côté du commercial, pas à sa place | Qualité (Epic 9) | Carousel workflow | Carousel 5 slides : mode parallèle, comparaison IA vs humain, convergence progressive, métriques confiance | **Haute** |
| 30 | 2026-10-20 (mar) | T.30 | Bilan final : d'un prototype à un vrai outil industriel | Conclusion | Carousel récap final | Carousel 6-8 slides : timeline du projet, métriques clés par epic, leçons apprises, la suite | **Haute** |

## Priorités expliquées

### Haute priorité (posts à publier en premier si changement de calendrier)

Ces posts résonnent le plus avec l'audience cible (décideurs industriels, pas ingénieurs) :

- **T.1** : Accroche initiale, résultats concrets, premier contact avec l'audience
- **T.3** : Problème universellement reconnu par les industriels (données sales)
- **T.5** : Spécifique au marché francophone, différenciation forte (jargon industriel français)
- **T.11** : Réponse à une vraie inquiétude des décideurs ("l'IA va-t-elle se tromper sans prévenir ?")
- **T.14** : Message stratégique clé (humain dans la boucle, pas remplacement)
- **T.15** : Récap boucle complète, démo du flux entier
- **T.16** : Mémoire industrie, sujet très parlant pour les décideurs (l'IA comprend MON métier)
- **T.18** : Personnalisation client, impact business immédiat et visible
- **T.23** : Dashboard, visuel fort, "je contrôle ce que fait l'IA"
- **T.29** : Mode cohabitation, rassure sur le rôle de l'humain
- **T.30** : Bilan final, récap émotionnel + métriques du parcours complet

### Moyenne priorité

Posts solides qui apportent de la crédibilité technique tout en restant accessibles :

- **T.2, T.4, T.6, T.7, T.10, T.12, T.13** : Mix résultats concrets et profondeur technique (Epics 1-4)
- **T.17, T.19, T.20, T.21** : Mémoire et apprentissage (Epic 6), crédibilité IA appliquée
- **T.22, T.24, T.25** : Observabilité et traçabilité (Epic 7), confiance et audit
- **T.26, T.27, T.28** : Configuration et qualité (Epics 8-9), adaptabilité entreprise

### Basse priorité

Posts plus techniques, intéressants mais moins engageants pour l'audience non technique :

- **T.8, T.9** : Deep dives recherche, excellents pour crédibilité mais audience plus étroite

## Phases de republication

| Phase | Posts | Semaines | Thème global |
|-------|-------|----------|--------------|
| Lancement | T.1 | Semaine 1 | "Regardez ce que l'IA peut faire pour vos devis" |
| Fondation (Epic 1) | T.2-T.4 | Semaines 2-4 | Choix tech, défis données, infrastructure solide |
| Pipeline Email (Epic 2) | T.5-T.7 | Semaines 5-7 | Comprendre le langage industriel, traiter les vrais emails |
| Recherche (Epic 3) | T.8-T.10 | Semaines 8-10 | Trouver le bon produit dans 50K références |
| Intelligence (Epic 4) | T.11-T.13 | Semaines 11-13 | Confiance, mémoire, raisonnement adaptatif |
| Boucle complète (Epic 5) | T.14-T.15 | Semaines 14-15 | La collaboration humain-IA, le pipeline entier |
| Mémoire et apprentissage (Epic 6) | T.16-T.21 | Semaines 16-21 | L'IA qui apprend de chaque interaction |
| Observabilité (Epic 7) | T.22-T.25 | Semaines 22-25 | Voir, comprendre et auditer ce que fait l'IA |
| Configuration (Epic 8) | T.26-T.27 | Semaines 26-27 | Un agent adaptable à chaque entreprise |
| Qualité et cohabitation (Epic 9) | T.28-T.29 | Semaines 28-29 | Tests, confiance, travail côte à côte |
| Conclusion | T.30 | Semaine 30 | Bilan : d'un prototype à un outil industriel |

## Notes sur les posts futurs (T.15-T.30)

Les posts T.15 à T.30 sont planifiés mais pas encore rédigés. Ils seront créés au fur et à mesure que les Epics 6-9 seront développés. Les titres et formats visuels sont des recommandations qui pourront évoluer en fonction des résultats réels obtenus pendant le développement.

Les dates sont indicatives : elles supposent que chaque epic prend environ le même temps. En réalité, le calendrier s'ajustera au rythme réel de développement.
