# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.9 : Reranking LLM : comment l'IA trie les résultats de recherche
- **Phase :** Recherche (Epic 3)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Basse

---

## Asset visuel

- **Type :** Carousel technique
- **Description :** Carousel 4 slides : query, résultats bruts, reranking, résultat final avec scores
- **Dimensions :** 1080x1080px par slide
- **Outil suggéré :** Canva
- **Notes :** Slide 1 : la requête client ("inox DN100"). Slide 2 : résultats bruts de la recherche (dont des produits invendables). Slide 3 : le filtre de proposabilité en action. Slide 4 : résultat final trié avec scores. Compréhensible sans lire le texte.

---

## Post LinkedIn

La recherche vectorielle a trouvé le bon produit. Elle a aussi trouvé 200 produits qu'on ne peut pas vendre.

50 000 produits indexés avec des embeddings vectoriels, le système comprend le sens, pas juste les mots. Ça marchait en démo. En production, trois problèmes sont apparus vite.

La recherche vectorielle seule rate les codes produit exacts. Un client tape "TUB-304L-025" et la recherche sémantique essaie d'interpréter le sens au lieu de trouver la correspondance exacte. Les résultats incluent des produits abandonnés et en rupture. Et le jargon industriel comme "inox DN100" ne dit rien au moteur sans contexte.

J'ai ajouté trois couches. Une recherche hybride qui combine le sens et les mots-clés. Un filtre qui retire les produits invendables avant qu'ils n'apparaissent dans les résultats. Et un dictionnaire de jargon qui développe automatiquement les abréviations.

363 tests qui passent, recherche en moins de 3 secondes sur 50 000 produits, et les recherches répétées reviennent en moins d'une seconde grâce au cache.

Quand vous cherchez un produit au travail, est-ce que le système comprend vraiment ce que vous voulez dire ?

---

## Hashtags

#IA #TransformationDigitale #BuildInPublic #AI #IndustrieB2B

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

Post #9, suite de la phase Recherche. T.8 couvrait la fondation de recherche (embeddings, pgvector, modèle multilingue). Ce post montre les trois couches qui rendent la recherche utilisable en production. La semaine prochaine : le récap de la phase Recherche complète.
