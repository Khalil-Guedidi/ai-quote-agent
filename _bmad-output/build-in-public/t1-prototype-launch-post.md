# Template de post LinkedIn : Série Build in Public

## Métadonnées du post

- **Story :** T.1 : Lancement du prototype : voilà ce que l'IA fait pour vos devis
- **Phase :** Lancement
- **Date de rédaction :** 2026-03-23
- **Priorité :** Haute

---

## Asset visuel

- **Type :** Screenshot + schéma
- **Description :** Screenshot résultats prototype (96.2% précision, 2.9s latence) + schéma pipeline simplifié email-vers-devis
- **Dimensions :** 1200x627px (screenshot) + 1080x1080px (schéma)
- **Outil suggéré :** Capture d'écran annotée + Excalidraw
- **Notes :** Annoter le screenshot avec les métriques clés (flèches sur 96.2% et 2.9s). Le schéma doit montrer le flux en 4 étapes : email reçu, extraction, matching produit, devis brouillon. Compréhensible sans lire le texte.

---

## Post LinkedIn

96.2% de précision. 2.9 secondes par devis. Sur un catalogue de 680 produits industriels, sans nettoyage de données.

Après des années dans le devis industriel B2B, je connais la réalité du terrain. Un client envoie "vis M8x40 inox" par email. Quelqu'un dans l'équipe commerciale doit comprendre que ça veut dire "vis à tête hexagonale M8, acier inoxydable", retrouver la bonne référence dans l'ERP, et rédiger un devis. Des dizaines de fois par jour.

J'ai construit un agent IA qui fait tout ça automatiquement. L'email arrive, l'agent comprend la demande, cherche dans le catalogue produit, et crée un brouillon de devis dans l'ERP. En moins de 3 secondes.

Le prototype tourne. Maintenant, je reconstruis tout pour la production : Python, LangGraph, Claude. Avec du scoring de confiance, de la mémoire, et un humain dans la boucle quand l'IA hésite.

Premier post d'une série Build in Public, du début à la fin.

Combien de temps vos équipes passent sur les devis chaque jour ?

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

Premier post de la série Build in Public. Il pose le décor : les résultats du prototype, le problème métier (devis industriels manuels), et l'arc narratif à venir. La semaine prochaine : les choix de stack pour passer du prototype à la production.
