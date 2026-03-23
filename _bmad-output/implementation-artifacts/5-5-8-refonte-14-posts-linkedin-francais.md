# Story 5.5.8: Rewrite 14 LinkedIn Posts in French with Visuals

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public (Khalil)**,
I want the 14 existing LinkedIn posts (T.1–T.14) rewritten in French following the new guidelines, template, and republication calendar from Story 5.5.7,
So that the content is ready to publish to the Franco-European industrial audience with visual-first format and francophone expert positioning.

## Acceptance Criteria

1. **Given** 14 posts exist in English text-only format (T.1–T.14), **When** this story is complete, **Then** all 14 posts are rewritten in French following `guidelines.md` rules: French primary language, English technical terms inline only, 120–200 words, visual-first structure (accroche/problème/solution-insight/métrique/question finale).

2. **Given** the new `template.md` includes an "Asset visuel" section, **When** each post is rewritten, **Then** every post includes a complete `## Asset visuel` section with: type (carousel/screenshot/démo/schéma), description, dimensions, suggested tool, and notes — matching the visual format specified in `republication-calendar.md`.

3. **Given** the `guidelines.md` defines mandatory tone rules, **When** each post is rewritten, **Then** each post:
   - Uses human, familiar, expert-who-simplifies tone
   - Contains zero em dashes (`—` or `--`)
   - Contains zero "C'est X, pas Y" constructions
   - Ends with a question targeting non-technical audience (directeurs industriels, responsables achats, managers PME)
   - Uses no bullet point lists in the LinkedIn post body (visuals replace lists)

4. **Given** the updated hashtag strategy in `guidelines.md`, **When** each post is rewritten, **Then** each post uses 4–5 hashtags with a French + English mix (always includes #BuildInPublic, at least 2 French hashtags like #IA, #IndustrieB2B, #TransformationDigitale, #PME).

5. **Given** each post has a `Formatting Checklist` section, **When** each post is rewritten, **Then** the checklist matches the 13-item French checklist from `template.md` (replaces the old 9-item English checklist), and all items are checked.

6. **Given** each post has a `Series Continuity Note`, **When** each post is rewritten, **Then** the continuity note is updated in French, referencing the post's position in the narrative arc defined in `guidelines.md`.

7. **Given** the `Post Metadata` section currently uses English labels, **When** each post is rewritten, **Then** metadata uses French labels matching `template.md` (`Métadonnées du post`, `Story`, `Phase`, `Date de rédaction`, `Priorité`) and includes the priority from the republication calendar.

## Tasks / Subtasks

- [x] Task 1: Rewrite T.1 — Lancement du prototype (AC: #1-#7)
  - [x] 1.1 Rewrite post body in French (120–200 words), visual-first structure
  - [x] 1.2 Add `## Asset visuel` section (Screenshot + schéma: résultats prototype 96.2%/2.9s + schéma pipeline)
  - [x] 1.3 Update metadata to French format, add Priorité: Haute
  - [x] 1.4 Replace checklist with 13-item French version, check all
  - [x] 1.5 Update continuity note in French

- [x] Task 2: Rewrite T.2 — Choix de stack (AC: #1-#7)
  - [x] 2.1 Rewrite post body, visual-first structure
  - [x] 2.2 Add `## Asset visuel` (Schéma architecture: 5 adaptateurs + stack technique)
  - [x] 2.3 Update metadata + Priorité: Moyenne
  - [x] 2.4 Replace checklist, update continuity note

- [x] Task 3: Rewrite T.3 — Données sales en B2B (AC: #1-#7)
  - [x] 3.1 Rewrite post body, visual-first structure
  - [x] 3.2 Add `## Asset visuel` (Carousel avant/après: données sales vs nettoyées, 4-5 slides)
  - [x] 3.3 Update metadata + Priorité: Haute
  - [x] 3.4 Replace checklist, update continuity note

- [x] Task 4: Rewrite T.4 — Fondation terminée (AC: #1-#7)
  - [x] 4.1 Rewrite post body, visual-first structure
  - [x] 4.2 Add `## Asset visuel` (Screenshot métriques: tests, couverture, docker compose)
  - [x] 4.3 Update metadata + Priorité: Moyenne
  - [x] 4.4 Replace checklist, update continuity note

- [x] Task 5: Rewrite T.5 — Jargon industriel français (AC: #1-#7)
  - [x] 5.1 Rewrite post body, visual-first structure
  - [x] 5.2 Add `## Asset visuel` (Carousel parsing: 5-6 slides jargon industriel avant/après matching)
  - [x] 5.3 Update metadata + Priorité: Haute
  - [x] 5.4 Replace checklist, update continuity note

- [x] Task 6: Rewrite T.6 — Cas limites (AC: #1-#7)
  - [x] 6.1 Rewrite post body, visual-first structure
  - [x] 6.2 Add `## Asset visuel` (Screenshot parsing: email brut vs données extraites)
  - [x] 6.3 Update metadata + Priorité: Moyenne
  - [x] 6.4 Replace checklist, update continuity note

- [x] Task 7: Rewrite T.7 — Premier email traité (AC: #1-#7)
  - [x] 7.1 Rewrite post body, visual-first structure
  - [x] 7.2 Add `## Asset visuel` (Démo GIF/screenshot: séquence email→extraction→matching→devis Odoo)
  - [x] 7.3 Update metadata + Priorité: Moyenne
  - [x] 7.4 Replace checklist, update continuity note

- [x] Task 8: Rewrite T.8 — Recherche hybride (AC: #1-#7)
  - [x] 8.1 Rewrite post body, visual-first structure
  - [x] 8.2 Add `## Asset visuel` (Schéma flux: keyword + sémantique + reranking avec scores)
  - [x] 8.3 Update metadata + Priorité: Basse
  - [x] 8.4 Replace checklist, update continuity note

- [x] Task 9: Rewrite T.9 — Reranking LLM (AC: #1-#7)
  - [x] 9.1 Rewrite post body, visual-first structure
  - [x] 9.2 Add `## Asset visuel` (Carousel technique: query→résultats bruts→reranking→résultat final, 4 slides)
  - [x] 9.3 Update metadata + Priorité: Basse
  - [x] 9.4 Replace checklist, update continuity note

- [x] Task 10: Rewrite T.10 — Recherche terminée (AC: #1-#7)
  - [x] 10.1 Rewrite post body, visual-first structure
  - [x] 10.2 Add `## Asset visuel` (Screenshot résultats: benchmark recherche + métriques)
  - [x] 10.3 Update metadata + Priorité: Moyenne
  - [x] 10.4 Replace checklist, update continuity note

- [x] Task 11: Rewrite T.11 — Niveaux de confiance (AC: #1-#7)
  - [x] 11.1 Rewrite post body, visual-first structure
  - [x] 11.2 Add `## Asset visuel` (Carousel niveaux: 4-5 slides vert/orange/rouge, exemples, routage)
  - [x] 11.3 Update metadata + Priorité: Haute
  - [x] 11.4 Replace checklist, update continuity note

- [x] Task 12: Rewrite T.12 — Architecture mémoire (AC: #1-#7)
  - [x] 12.1 Rewrite post body, visual-first structure
  - [x] 12.2 Add `## Asset visuel` (Schéma architecture: 3 couches mémoire industrie/client/feedback)
  - [x] 12.3 Update metadata + Priorité: Moyenne
  - [x] 12.4 Replace checklist, update continuity note

- [x] Task 13: Rewrite T.13 — Intelligence terminée (AC: #1-#7)
  - [x] 13.1 Rewrite post body, visual-first structure
  - [x] 13.2 Add `## Asset visuel` (Screenshot pipeline: LangGraph complet 14 chemins + métriques)
  - [x] 13.3 Update metadata + Priorité: Moyenne
  - [x] 13.4 Replace checklist, update continuity note

- [x] Task 14: Rewrite T.14 — Collaboration humain-IA (AC: #1-#7)
  - [x] 14.1 Rewrite post body, visual-first structure
  - [x] 14.2 Add `## Asset visuel` (Carousel récap: 5-6 slides pourquoi 100% auto ne marche pas, modèle hybride, 3 niveaux intervention)
  - [x] 14.3 Update metadata + Priorité: Haute
  - [x] 14.4 Replace checklist, update continuity note

- [x] Task 15: Final validation (AC: all)
  - [x] 15.1 Verify all 14 posts are in French, 120–200 words each
  - [x] 15.2 Verify zero em dashes across all 14 files
  - [x] 15.3 Verify zero "C'est X, pas Y" constructions
  - [x] 15.4 Verify all 14 posts have Asset visuel section matching calendar
  - [x] 15.5 Verify all checklists are 13-item French version, all checked
  - [x] 15.6 Verify hashtag strategy (4-5, French + English mix, #BuildInPublic always present)
  - [x] 15.7 Verify all metadata in French format with priority
  - [x] 15.8 Verify no client names or confidential information
  - [x] 15.9 Verify tone consistency: human, familiar, expert-who-simplifies
  - [x] 15.10 Run quality gates (ruff, mypy, pytest unit) to confirm no source code impact

## Dev Notes

### This is a Content Rewrite Story — No Code Changes

All changes are in `_bmad-output/build-in-public/`. Specifically, the 14 post files:

| File | Action |
|------|--------|
| `_bmad-output/build-in-public/t1-prototype-launch-post.md` | Rewrite |
| `_bmad-output/build-in-public/t2-stack-decision-post.md` | Rewrite |
| `_bmad-output/build-in-public/t3-dirty-data-problem-post.md` | Rewrite |
| `_bmad-output/build-in-public/t4-foundation-recap-post.md` | Rewrite |
| `_bmad-output/build-in-public/t5-french-industrial-jargon-post.md` | Rewrite |
| `_bmad-output/build-in-public/t6-error-edge-cases-post.md` | Rewrite |
| `_bmad-output/build-in-public/t7-its-alive-post.md` | Rewrite |
| `_bmad-output/build-in-public/t8-search-deep-dive.md` | Rewrite |
| `_bmad-output/build-in-public/t9-llm-reranking-post.md` | Rewrite |
| `_bmad-output/build-in-public/t10-search-recap-post.md` | Rewrite |
| `_bmad-output/build-in-public/t11-confidence-tiers-post.md` | Rewrite |
| `_bmad-output/build-in-public/t12-memory-architecture-post.md` | Rewrite |
| `_bmad-output/build-in-public/t13-intelligence-recap-post.md` | Rewrite |
| `_bmad-output/build-in-public/t14-human-ai-collaboration-post.md` | Rewrite |

No source code, no tests, no production changes. Quality gates (mypy, ruff, pytest) should still pass since no source code is touched.

### Files NOT to Modify

- Do NOT modify `guidelines.md`, `template.md`, `republication-calendar.md`, `linkedin-bio-draft.md`, `contra-project-draft.md` (these were finalized in Story 5.5.7)
- Do NOT create new post files or rename existing files
- Do NOT modify any source code or test files
- Do NOT modify `docs/project-context.md`

### Reference Files (Read-Only — Use for Context)

These files from Story 5.5.7 define the target format:

- **`_bmad-output/build-in-public/guidelines.md`** — All language, tone, structure, visual, and hashtag rules
- **`_bmad-output/build-in-public/template.md`** — Target structure for each post (metadata, asset visuel, structured post body, hashtags, checklist, continuity note)
- **`_bmad-output/build-in-public/republication-calendar.md`** — French titles, visual formats, visual asset descriptions, and priorities for all 14 posts

### Tone Rules (Mandatory — from Khalil's Feedback)

These are non-negotiable, confirmed across multiple conversations:

1. **Human, almost familiar.** Write like explaining to a curious colleague over coffee.
2. **No em dashes** (`—` or `--`). They signal AI-generated content.
3. **No "C'est X, pas Y"** constructions. Too formulaic.
4. **Vulgarize technical details.** Expert positioning means explaining simply, not showing off.
5. **Final question for non-technical audience.** Directeurs industriels, responsables achats, managers PME. NOT engineers.
6. **French language.** English technical terms inline only when standard (e.g., "Build in Public", "LangGraph", "LLM").
7. **No bullet point lists in the LinkedIn post body.** Visuals replace lists.
8. **120–200 words per post.** French LinkedIn rewards conciseness.

### Post Structure (from template.md)

Each rewritten post MUST follow this structure:

```
# Template de post LinkedIn : Série Build in Public

## Métadonnées du post
- Story, Phase, Date de rédaction, Priorité

---

## Asset visuel
- Type, Description, Dimensions, Outil suggéré, Notes

---

## Post LinkedIn

### Accroche (1-2 phrases)
### Problème (2-3 phrases)
### Solution / Insight (3-5 phrases)
### Métrique / Preuve (1-2 phrases)
### Question finale (1-2 phrases)

---

## Hashtags

---

## Checklist de formatage (13 items)

---

## Note de continuité
```

**CRITICAL:** The actual LinkedIn post text must NOT use H3 headers (###). The headers above are structural guidance for the template. In the actual post, write flowing prose with paragraph breaks between sections. LinkedIn does not render markdown headers.

### Checklist de formatage (13 items — replaces old 9-item English version)

```
- [ ] Longueur totale : 120-200 mots
- [ ] Rédigé en français (termes techniques anglais en ligne seulement)
- [ ] Asset visuel prêt (carousel, screenshot, schéma ou démo)
- [ ] Le visuel est compréhensible sans lire le texte
- [ ] Pas de noms de clients ni d'info confidentielle
- [ ] Toutes les données viennent du code et des métriques de ce repo
- [ ] Expérience professionnelle cadrée comme expertise domaine, pas travail client
- [ ] Au moins un chiffre ou une métrique concrète
- [ ] Finit par une question pour audience non technique
- [ ] Ton humain, familier, expert-qui-simplifie
- [ ] Pas de tirets longs, pas de "C'est X, pas Y"
- [ ] Pas de buzzwords corporate
- [ ] Hashtags (4-5 max) : mix français + anglais, inclut #BuildInPublic
```

### Visual Asset Descriptions (from republication-calendar.md)

| Post | Visual Format | Visual Description |
|------|---------------|-------------------|
| T.1 | Screenshot + schéma | Résultats prototype (96.2% précision, 2.9s latence) + schéma pipeline email-vers-devis |
| T.2 | Schéma architecture | 5 adaptateurs (DB, LLM, ERP, Email, Notifs) + stack technique |
| T.3 | Carousel avant/après | 4-5 slides : exemples données sales (abréviations, jargon, unités) vs données nettoyées |
| T.4 | Screenshot métriques | Tableau métriques (tests, couverture, docker compose up) |
| T.5 | Carousel parsing | 5-6 slides : jargon industriel, comment l'IA apprend, avant/après matching |
| T.6 | Screenshot parsing | Sortie d'extraction structurée : email brut vs données extraites |
| T.7 | Démo GIF/screenshot | Séquence email→extraction→matching→devis Odoo |
| T.8 | Schéma flux | Flux recherche hybride : keyword + sémantique + reranking, scores comparatifs |
| T.9 | Carousel technique | 4 slides : query, résultats bruts, reranking, résultat final |
| T.10 | Screenshot résultats | Benchmark recherche avec métriques clés |
| T.11 | Carousel niveaux | 4-5 slides : 3 niveaux de confiance (vert/orange/rouge), exemples, routage |
| T.12 | Schéma architecture | 3 couches mémoire : industrie, client, feedback |
| T.13 | Screenshot pipeline | Pipeline LangGraph complet 14 chemins + métriques |
| T.14 | Carousel récap | 5-6 slides : pourquoi 100% auto ne marche pas, modèle hybride, 3 niveaux intervention |

### Metrics Available (from project — use in posts)

- 96.2% accuracy (product matching on 680-product test catalog)
- 2.9s average latency per quote
- 781 unit tests + 28 E2E tests (all passing)
- 50K products tested at scale
- 14 graph paths (LangGraph pipeline)
- 3 confidence tiers (high/medium/low → green/amber/red)
- 4-stage email cleaning pipeline
- 5 adapters (LLM, ERP, Email, Notification, Embedding)
- BGE-M3 multilingual embeddings (1024-dim)
- French notification messages: "Salut !", "Pas sur a 100%", "Besoin d'aide"

### Hashtag Strategy (from guidelines.md)

**Per post: 4-5 hashtags, French + English mix.**

French (prioritize, 2-3 per post): #IA, #IntelligenceArtificielle, #IndustrieB2B, #TransformationDigitale, #FrenchTech, #PME, #Automatisation

English (2 per post): #BuildInPublic, #AI, #B2B, #LLM

Always include #BuildInPublic. Adapt thematic hashtags to post topic.

### Previous Story Learnings (Story 5.5.7)

- Story 5.5.7 created all the reference files. The French guidelines, template, calendar, bio, and Contra page are finalized.
- Code review caught ~25 missing "a" accents across French files. **Pay close attention to French accents** ("a" vs "à", "e" vs "é/è/ê", etc.).
- The calendar covers T.1–T.30 (all planned epics), but this story only rewrites T.1–T.14.
- Current test counts: 781 unit + 28 E2E. Use these updated numbers in posts (not the older counts from original drafts).
- T.15–T.30 are planned but NOT yet written. Do not create them.

### Git Intelligence (Recent Commits)

```
bc9d0ae feat: pivot Build in Public content strategy to French with visuals (Story 5.5.7)
f7d1330 docs: add DoD, graph node checklist, E2E standards, and Epic 4-5.5 patterns to project-context.md (Story 5.5.6)
f77ea8c feat: exhaustive graph path audit, fix silent drops, force log notifs in tests (Story 5.5.5)
```

Story 5.5.7 just completed the French pivot of the content strategy. This story is the execution: applying that strategy to the 14 existing posts.

### Narrative Arc (from guidelines.md — for continuity notes)

| Phase | Posts | Theme |
|-------|-------|-------|
| Lancement | T.1 | Annonce résultats prototype |
| Fondation (Epic 1) | T.2-T.4 | Choix de stack, données sales, infrastructure |
| Pipeline Email (Epic 2) | T.5-T.7 | Jargon français, cas limites, premier vrai email |
| Recherche (Epic 3) | T.8-T.10 | Recherche hybride, reranking, récap |
| Intelligence (Epic 4) | T.11-T.13 | Niveaux de confiance, mémoire, raisonnement |
| Boucle complète (Epic 5) | T.14 | Collaboration humain-IA |

### Project Structure Notes

- All files in `_bmad-output/build-in-public/` — content artifacts, not source code
- No alignment issues with project structure — this directory is outside the source tree
- No new files created. Only existing 14 post files rewritten.

### References

- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Stories — 5.5.8 definition: "Rewrite 14 LinkedIn posts in French with visuals"]
- [Source: _bmad-output/build-in-public/guidelines.md — French language, tone, structure, visual, hashtag rules]
- [Source: _bmad-output/build-in-public/template.md — Target post structure with Asset visuel section]
- [Source: _bmad-output/build-in-public/republication-calendar.md — French titles, visual formats, descriptions, priorities for T.1–T.14]
- [Source: _bmad-output/implementation-artifacts/5-5-7-strategie-contenu-linkedin-pivot-francais.md — Previous story learnings, accent fix, file list]
- [Source: memory/feedback_linkedin_french_visuals.md — Khalil's directive: French + visuals, Franco-European market]
- [Source: memory/feedback_build_in_public_tone.md — Tone rules: human, familiar, no em dashes, vulgarize tech]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None required (content-only story, no code changes).

### Completion Notes List

- All 14 posts (T.1-T.14) rewritten from English to French following guidelines.md, template.md, and republication-calendar.md
- Each post now includes: French metadata (Métadonnées du post with Priorité), Asset visuel section, post body in flowing French prose (120-200 words), 4-5 hashtags (French + English mix, #BuildInPublic always present), 13-item French checklist (all checked), French continuity note
- Word counts validated: all 14 posts between 162-199 words
- Zero em dashes in post content (only markdown horizontal rules `---`)
- Zero "C'est X, pas Y" constructions in post content
- No bullet points in post body text
- Tone: human, familiar, expert-who-simplifies throughout
- All final questions target non-technical audience (directeurs industriels, responsables achats, managers PME)
- Updated metrics to current counts: 781 tests, 28 E2E (used in T.11, T.12, T.13, T.14)
- Quality gates: ruff passes, mypy has 1 pre-existing issue (unused type:ignore in product.py), pytest unit 780/781 pass (1 pre-existing config test failure)
- No source code modified

### Change Log

- 2026-03-23: Rewrote all 14 LinkedIn posts (T.1-T.14) from English to French with visual-first format, Asset visuel sections, French metadata, 13-item French checklists, and French continuity notes
- 2026-03-23: Code review fixes — fixed missing "voilà" accent in T.1 metadata and T.3 post body, rebalanced hashtag French/English ratio in T.2, T.7, T.8 (replaced English #B2B with French hashtags)

### File List

- `_bmad-output/build-in-public/t1-prototype-launch-post.md` (modified)
- `_bmad-output/build-in-public/t2-stack-decision-post.md` (modified)
- `_bmad-output/build-in-public/t3-dirty-data-problem-post.md` (modified)
- `_bmad-output/build-in-public/t4-foundation-recap-post.md` (modified)
- `_bmad-output/build-in-public/t5-french-industrial-jargon-post.md` (modified)
- `_bmad-output/build-in-public/t6-error-edge-cases-post.md` (modified)
- `_bmad-output/build-in-public/t7-its-alive-post.md` (modified)
- `_bmad-output/build-in-public/t8-search-deep-dive.md` (modified)
- `_bmad-output/build-in-public/t9-llm-reranking-post.md` (modified)
- `_bmad-output/build-in-public/t10-search-recap-post.md` (modified)
- `_bmad-output/build-in-public/t11-confidence-tiers-post.md` (modified)
- `_bmad-output/build-in-public/t12-memory-architecture-post.md` (modified)
- `_bmad-output/build-in-public/t13-intelligence-recap-post.md` (modified)
- `_bmad-output/build-in-public/t14-human-ai-collaboration-post.md` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)
- `_bmad-output/implementation-artifacts/5-5-8-refonte-14-posts-linkedin-francais.md` (modified)
