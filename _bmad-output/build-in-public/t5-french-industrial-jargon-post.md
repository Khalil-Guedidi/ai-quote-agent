# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.5 : "Vis M8x40 inox" : quand l'IA doit apprendre le jargon industriel français
- **Phase :** Pipeline Email (Epic 2)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Haute

---

## Asset visuel

- **Type :** Carousel parsing
- **Description :** Carousel 5-6 slides : exemples jargon industriel, comment l'IA apprend à les décoder, avant/après matching
- **Dimensions :** 1080x1080px par slide
- **Outil suggéré :** Canva
- **Notes :** Slide 1 : titre avec exemples de jargon (DN100, PN16, inox 316L). Slides 2-3 : exemples d'emails réels avec abréviations. Slide 4 : le pipeline de nettoyage en 4 étapes. Slide 5 : avant/après (email brut vs données extraites). Slide 6 : métrique (18 tests). Chaque slide lisible seule.

---

## Post LinkedIn

"50 vannes papillon DN100 en inox 316L." Toute une demande produit en une ligne. Et totalement illisible si vous ne travaillez pas dans la fourniture industrielle française.

Je construis un agent IA qui traite les demandes de devis B2B par email. Le premier vrai défi ? Nettoyer les emails. Chaque message arrive noyé dans des fils de réponse et des signatures. Il faut virer tout ce bruit. Sauf que les données importantes ressemblent exactement à du bruit pour un parser générique.

DN100, c'est un diamètre de tuyau. PN16, une classe de pression. Inox 316L, un alliage inoxydable. Ø veut dire diamètre, lg veut dire longueur. Ces abréviations SONT la demande. Si on les supprime, il ne reste rien à chiffrer.

J'ai construit un pipeline en 4 étapes qui fait la différence entre "Cordialement, Sophie" (signature, on supprime) et "DN50 PN16 en acier" (spec produit, on garde). Si le nettoyeur supprime plus de 90% du contenu, un garde-fou renvoie l'original.

18 tests rien que pour cette étape. Parce que quand on décide quoi garder et quoi jeter, il faut avoir raison.

Quelle est l'abréviation la plus bizarre que votre industrie utilise, et qu'un outsider ne comprendrait jamais ?

---

## Hashtags

#IA #FrenchTech #BuildInPublic #AI #IndustrieB2B

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

Post #5, premier de la phase Pipeline Email (Epic 2). T.4 fermait la phase Fondation. Ce post entre dans le vif du sujet : le jargon industriel français que l'IA doit comprendre sans le supprimer. La semaine prochaine : les cas limites, quand un email contient 12 produits et 3 langues.
