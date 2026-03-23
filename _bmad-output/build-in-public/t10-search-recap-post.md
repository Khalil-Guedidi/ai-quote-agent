# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.10 : Recherche terminée : 50K produits, 96% de précision
- **Phase :** Recherche (Epic 3)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Screenshot résultats
- **Description :** Screenshot benchmark résultats recherche avec métriques clés
- **Dimensions :** 1200x627px
- **Outil suggéré :** Capture d'écran annotée
- **Notes :** Montrer les métriques de benchmark : 96% de précision, recherche sous 3 secondes, 50 000 produits, cache sous 1 seconde. Annoter les chiffres clés avec des encadrés. Compréhensible sans lire le texte.

---

## Post LinkedIn

J'ai construit une fonctionnalité, je l'ai benchmarkée, et je l'ai supprimée. Probablement ma meilleure décision technique du mois.

Mon agent IA cherche dans 50 000 produits industriels. Quand je l'ai testé sur des abréviations comme "inox" ou "DN100", le moteur ratait parfois. Alors j'ai fait ce que j'ai toujours fait : j'ai construit un dictionnaire de jargon. Des tables de synonymes qui traduisent les abréviations en termes complets. J'ai livré ce pattern exact avant. Ça marche. Ça grossit aussi indéfiniment, et au final plus personne n'ose y toucher.

C'est ce qui me gênait après l'avoir poussé. J'avais vu ces tables devenir des cauchemars de maintenance. Et si le modèle IA était déjà assez bon tout seul ?

J'ai lancé le benchmark sans le dictionnaire. 96% de précision sur 25 requêtes de jargon. Le modèle comprenait déjà que "inox" veut dire acier inoxydable. Mon expérience me disait de construire la table. Les données me disaient de la supprimer.

Supprimée. 9 stories, 175 nouveaux tests, zéro régression. Recherche sous 3 secondes sur 50 000 produits. Le tout avec une seule base PostgreSQL.

Vous est-il déjà arrivé de résoudre un problème par habitude, pour réaliser ensuite que le problème n'existait plus ?

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

Post #10, dernier de la phase Recherche (Epic 3). T.9 montrait les trois couches de recherche en production. Ce post ferme la phase avec l'histoire du dictionnaire de jargon : construit, benchmarké, supprimé. Les données ont eu le dernier mot. La semaine prochaine : la phase Intelligence (Epic 4) commence avec les niveaux de confiance.
