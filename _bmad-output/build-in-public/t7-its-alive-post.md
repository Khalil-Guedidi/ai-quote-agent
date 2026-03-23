# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.7 : Premier vrai email traité de bout en bout
- **Phase :** Pipeline Email (Epic 2)
- **Date de rédaction :** 2026-03-23
- **Priorité :** Moyenne

---

## Asset visuel

- **Type :** Démo GIF/screenshot
- **Description :** GIF ou screenshot séquence : email reçu, extraction, matching, devis brouillon dans Odoo
- **Dimensions :** 1200x627px ou GIF
- **Outil suggéré :** Capture d'écran annotée ou enregistrement terminal
- **Notes :** Montrer la séquence complète en 4 étapes avec des flèches : email IMAP reçu, contenu nettoyé, données extraites, résultat structuré. Annoter chaque étape. Compréhensible sans lire le texte.

---

## Post LinkedIn

La semaine dernière, mon système a traité son premier vrai email. Pas un fichier de test. Pas une chaîne codée en dur. Une vraie demande de devis B2B, reçue, analysée et structurée automatiquement.

Le prototype que j'avais construit faisait 96.2% de précision sur le matching produit. Une belle démo. Mais il ne savait pas recevoir un email tout seul. Il ne gérait pas les données manquantes, le mauvais formatage, ou quelqu'un qui essaie de tromper le modèle.

J'ai tout reconstruit. 2 epics, 14 stories, et quelques semaines plus tard, le système reçoit les emails par IMAP, nettoie les signatures et le bruit, extrait les données structurées avec un LLM, et sépare les demandes multi-produits en lignes individuelles. 4 étapes, chacune avec sa propre gestion d'erreurs.

Le prototype avait zéro test. Le pipeline de production en a 188. Le prototype était un flux monolithique. La production, ce sont 4 étapes distinctes avec des couches de sécurité et de la dégradation gracieuse à chaque niveau.

Le pipeline est vivant. Les emails entrent, les données structurées sortent.

À quel moment votre projet perso a commencé à ressembler à un vrai produit ?

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

Post #7, dernier de la phase Pipeline Email (Epic 2). T.6 montrait la gestion des erreurs et cas limites. Ce post marque le jalon : le pipeline fonctionne de bout en bout. La semaine prochaine, la série entre dans la phase Recherche (Epic 3) : trouver le bon produit parmi 50 000 références.
