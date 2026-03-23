# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.8 : Recherche hybride : ni keyword ni sémantique seul ne suffit
- **Phase :** Recherche (Epic 3)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Basse

---

## Asset visuel

- **Type :** Schéma flux
- **Description :** Diagramme flux recherche hybride : keyword + sémantique + reranking, avec scores comparatifs
- **Dimensions :** 1200x627px
- **Outil suggéré :** Excalidraw ou Mermaid
- **Notes :** Montrer 3 branches parallèles (keyword, sémantique, fusion) qui convergent vers un résultat final. Ajouter des exemples de scores à chaque étape. Inclure BGE-M3 et pgvector comme étiquettes. Compréhensible sans lire le texte.

---

## Post LinkedIn

96.2% de précision sur 680 produits. Est-ce que ça tient sur 50 000 ?

Mon agent IA sait recevoir des emails et extraire des données structurées. Mais extraire "vanne papillon DN100 inox" ne sert à rien si on ne trouve pas le bon produit dans un catalogue de 50 000 références. Et la recherche par mots-clés seule ne suffit pas.

Les catalogues industriels sont un bazar. Le même produit a trois noms selon qui a rédigé la fiche technique. Les abréviations cohabitent avec les noms complets. Le français et l'anglais se mélangent dans le même catalogue. Une recherche texte sur "vanne papillon" ne trouvera jamais "butterfly valve", alors que c'est le même produit. Il faut une recherche qui comprend le sens, pas seulement les mots.

J'ai construit la fondation d'une recherche hybride. Étape 1 : ingérer 50 000 produits depuis l'ERP sans nettoyage manuel. Étape 2 : générer des embeddings vectoriels avec un modèle multilingue (BGE-M3, 1024 dimensions) qui gère le jargon industriel français nativement. Le tout stocké dans PostgreSQL avec pgvector. Une seule base pour les données relationnelles et la recherche vectorielle.

Vous avez déjà testé la recherche vectorielle sur des données produit multilingues et mal formatées ?

---

## Hashtags

#IA #IndustrieB2B #BuildInPublic #AI #Automatisation

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

Post #8, premier de la phase Recherche (Epic 3). T.7 fermait la phase Pipeline Email avec le jalon "ça vit". Ce post attaque le nouveau défi : trouver le bon produit parmi 50 000 références. La semaine prochaine : le reranking LLM, comment l'IA trie les résultats de recherche.
