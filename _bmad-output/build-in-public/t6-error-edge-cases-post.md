# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.6 : Cas limites : quand un email contient 12 produits et 3 langues
- **Phase :** Pipeline Email (Epic 2)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Screenshot parsing
- **Description :** Screenshot sortie d'extraction structurée : email brut vs données extraites par le LLM
- **Dimensions :** 1200x627px
- **Outil suggéré :** Capture d'écran annotée
- **Notes :** Côté gauche : email brut avec du bruit (signatures, fils de réponse). Côté droit : données structurées extraites (produits, quantités, références). Flèches entre les deux pour montrer la transformation. Compréhensible sans lire le texte.

---

## Post LinkedIn

Chaque démo IA montre le cas idéal. Le modèle reçoit une entrée propre, produit une sortie parfaite, tout le monde applaudit. Mais la production, ce n'est pas une démo.

Je construis un agent IA qui transforme des emails de demande de devis B2B en données structurées. Parfois l'email est vide. Parfois le modèle met 15 secondes à répondre. Parfois l'extraction renvoie un produit sans quantité, sans référence, juste une description vague. Qu'est-ce qui se passe dans ces cas-là ?

On anticipe. Chaque échec a sa stratégie.

Si le modèle met trop longtemps, un timeout de 10 secondes coupe l'appel proprement. Si l'extraction échoue sur un email, cet email est signalé et le pipeline passe au suivant. Si le modèle ne trouve pas de quantité, le champ reste vide. Pas d'invention. Pas de données hallucinées. Le pipeline continue.

166 tests à ce stade. Parce que le cas idéal, c'est peut-être 10% du code. Les 90% restants ? S'assurer que le système survit au monde réel.

Quand vous déployez une fonctionnalité IA, quel est votre plan pour quand le modèle ne marche tout simplement pas ?

---

## Hashtags

#IA #Automatisation #BuildInPublic #AI #IndustrieB2B

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

Post #6, suite de la phase Pipeline Email. T.5 montrait le défi du jargon industriel français. Ce post montre ce qui se passe quand le pipeline rencontre un mur : les cas limites et la gestion d'erreurs. La semaine prochaine : le premier vrai email traité de bout en bout.
