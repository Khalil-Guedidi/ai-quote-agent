# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.12 : Architecture mémoire : comment l'agent apprend de chaque devis
- **Phase :** Intelligence (Epic 4)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Schéma architecture
- **Description :** Diagramme mémoire : knowledge base industrie, contexte client, historique feedback
- **Dimensions :** 1200x627px
- **Outil suggéré :** Excalidraw ou Mermaid
- **Notes :** Montrer 3 couches empilées : industrie (standards acier, terminologie), entreprise (noms produits, fournisseurs), client (historique commandes, préférences). Flèches montrant comment un nouveau client bénéficie des 3 couches dès le premier jour. Compréhensible sans lire le texte.

---

## Post LinkedIn

La plupart des outils IA traitent chaque demande comme si c'était la première. Aucune mémoire de ce qui a marché hier, aucun contexte sur qui demande.

Dans le devis industriel B2B, c'est un vrai problème. Le client X veut toujours du 304L quand il dit "inox". L'entreprise propose systématiquement du galvanisé pour l'extérieur. Et DN25, c'est 25mm de diamètre nominal dans toute l'industrie. Trois couches de connaissance, trois périmètres différents. Une IA qui ignore tout ça repart de zéro à chaque fois.

J'ai conçu une mémoire en 3 couches pour mon agent. Couche 1 : la connaissance industrie (standards acier, terminologie, conventions partagées). Couche 2 : les règles entreprise (noms produits, fournisseurs préférés, contraintes métier). Couche 3 : la mémoire client (historique commandes, préférences, corrections passées).

Un nouveau client bénéficie des trois couches dès le premier jour. Même sans historique personnel, l'agent applique les connaissances industrie et entreprise. Avec le temps, il apprend : Sophie corrige un brouillon (mauvaise épaisseur), et la prochaine fois l'agent s'en souvient.

La plomberie fonctionne déjà. L'agent lit l'historique depuis l'ERP et écrit des brouillons de devis. 781 tests, zéro régression.

Dans votre métier, quelle connaissance aimeriez-vous que vos outils retiennent entre chaque demande ?

---

## Hashtags

#IA #IndustrieB2B #BuildInPublic #AI #PME

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

Post #12, suite de la phase Intelligence. T.11 montrait les niveaux de confiance (comment l'agent gère l'incertitude). Ce post va plus loin : l'agent lit et écrit dans l'ERP, et l'architecture mémoire en 3 couches est conçue pour s'appuyer sur cette infrastructure de données. La semaine prochaine : le récap de la phase Intelligence complète.
