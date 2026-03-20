# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.10 — Search Recap Post
- **Phase:** Search (Epic 3)
- **Date drafted:** 2026-03-20

---

## LinkedIn Post

I built a feature, benchmarked it, and then deleted the entire thing. That might be the best engineering decision I made this month.

My AI quote agent searches through 50,000 industrial products. When I tested it on abbreviations like "inox" or "DN100", the search engine sometimes missed. So I did what I've always done on past projects: I built a jargon dictionary. Synonym tables that translate industry shorthand into full terms before searching. I've shipped this exact pattern before. It works. It also grows forever, drifts, and eventually nobody dares to touch it.

And that's what kept bugging me after I pushed it. I'd seen these tables turn into maintenance nightmares at scale. What if the AI model was already good enough on its own?

So I ran the benchmark without the dictionary. 96% accuracy on 25 jargon queries. The model already understood "inox" means stainless steel. My experience told me to build the table. The data told me to delete it.

Deleted it. Nine stories, 175 new tests, zero regressions. Search runs under 3 seconds on 50,000 products. All powered by a single PostgreSQL database. No separate search service, no Redis, no Elasticsearch.

Sometimes the hardest thing isn't building. It's unlearning what worked before.

Have you ever caught yourself solving a problem out of habit, only to realize it didn't exist anymore?

#BuildInPublic #AI #Search #B2B #Python

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 228 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (50,000 products, 96%, 25 queries, 175 tests, 3 seconds, 9 stories)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #Search #B2B #Python

---

## Series Continuity Note

This is post #10 in the Build in Public series and the final post in the Search phase (Epic 3). T.8 covered the search foundation (vector embeddings, 50K products). T.9 showed the production layers (hybrid search, proposability filter, jargon dictionary). T.10 wraps up by telling the story of building and removing the jargon dictionary, plus the full phase metrics. Next: T.11 transitions to the Intelligence phase (Epic 4) with confidence tiers.

---

## Contra Project Update

**Epic 3 Complete: Intelligent Product Search**

The AI quote agent now has a fully functional search pipeline. From email extraction to product matching:

- **Pipeline:** 5-stage search (ingestion, embeddings, hybrid search, proposability filter, cache) powered entirely by PostgreSQL
- **Quality:** 363 automated tests (up from 188 at Epic 2), 9/9 stories delivered, 0 regressions
- **Scale:** 50,000 products indexed with BGE-M3 multilingual embeddings, sub-3s search latency, sub-1s cached results
- **Architecture:** PostgreSQL-only (pgvector for semantic, tsvector for keywords, SQL for filtering, table for cache). No Redis. No Elasticsearch.
- **Validation:** Jargon dictionary built then removed after benchmark confirmed 96% accuracy with semantic search alone. Zero-preprocessing vision preserved.

**What's next:** Epic 4 brings adaptive reasoning and quote generation. The system can find products. Next it learns to assess confidence and generate actual quotes.
