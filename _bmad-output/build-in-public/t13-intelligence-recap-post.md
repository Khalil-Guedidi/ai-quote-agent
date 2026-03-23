# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.13 : Intelligence terminée : raisonnement adaptatif et auto-évaluation
- **Phase :** Intelligence (Epic 4)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Screenshot pipeline
- **Description :** Screenshot pipeline LangGraph complet avec 14 chemins et métriques
- **Dimensions :** 1200x627px
- **Outil suggéré :** Capture d'écran annotée
- **Notes :** Montrer le pipeline en 7 étapes (classifier, chercher, scorer, raisonner, auto-évaluer, conformité, brouillon). Annoter avec le nombre de chemins (14) et les métriques clés (781 tests, 28 E2E). Compréhensible sans lire le texte.

---

## Post LinkedIn

Mon agent IA savait trouver le bon produit dans 50 000 références. Mais trouver le bon produit, c'était juste la première étape. Le commercial devait encore décider quoi faire du résultat.

Dans le devis industriel B2B, l'écart entre "voici un produit" et "voici un devis" est l'endroit où la plupart des automatisations échouent. Demandes vagues, conformité, correspondances incertaines.

J'ai construit un pipeline en 7 étapes. Un email arrive. L'agent classe la demande par complexité, cherche les produits, évalue sa confiance, relit son propre travail, vérifie la conformité export, et crée un brouillon dans l'ERP. Chaque étape a une règle : si quelque chose ne va pas, demander à un humain.

J'ai aussi construit un dictionnaire de jargon, benchmarké, et supprimé. 96% de précision avec, 96% sans. Le modèle comprenait déjà le jargon.

781 tests, 28 E2E, zéro régression. 14 chemins dans le pipeline LangGraph.

L'agent sait réfléchir. Prochaine étape : s'assurer que le bon humain voit le résultat au bon moment.

Quand vous automatisez un processus, vous commencez par ce qui se passe quand ça marche, ou quand ça casse ?

---

## Hashtags

#IA #Automatisation #BuildInPublic #AI #LLM

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

Post #13, dernier de la phase Intelligence (Epic 4). T.11 couvrait les niveaux de confiance, T.12 l'architecture mémoire. Ce post ferme la phase en zoomant : le système a maintenant un pipeline de raisonnement complet en 7 étapes. Le rappel du dictionnaire de jargon fait écho au thème de T.10 ("construire, benchmarker, supprimer"). La semaine prochaine : la collaboration humain-IA et les notifications.
