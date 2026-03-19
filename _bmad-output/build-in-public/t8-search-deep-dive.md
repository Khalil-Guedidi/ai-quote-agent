# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.8 — Search Deep Dive Post
- **Phase:** Search (Epic 3)
- **Date drafted:** 2026-03-20

---

## LinkedIn Post

96.2% accuracy on 680 products. Will it hold on 50,000?

My AI quote agent can receive emails and extract structured data. But extracting "butterfly valve DN100 stainless steel" means nothing if you can't find the right product in a catalog with 50,000 references. That's the new problem. And keyword search alone won't solve it.

Industrial catalogs are messy. The same product has three names depending on who wrote the data sheet. Abbreviations mix with full names. French and English coexist in the same catalog. A text search for "vanne papillon" won't match "butterfly valve" even though they're the exact same product. You need a search that understands meaning, not just words.

So I built the foundation for hybrid search. Step one: ingest 50,000 products from the ERP with zero manual cleanup. Step two: generate vector embeddings using a multilingual model (BGE-M3, 1024 dimensions) that handles French industrial jargon out of the box. Store everything in PostgreSQL with pgvector. One database for relational data and vector search. No separate infrastructure to maintain.

Next step is combining vector search with keyword matching and fusing the results. The embedding layer is live. The search layer is next.

Have you tried vector search on messy, multilingual product data? What surprised you?

#BuildInPublic #AI #VectorSearch #B2B #Python

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 210 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (96.2%, 50,000 products, 1024 dimensions, 680 products)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #VectorSearch #B2B #Python

---

## Series Continuity Note

This is post #8 in the Build in Public series and the first post in the Search phase (Epic 3). T.7 closed the Email Pipeline phase with the "It's Alive" milestone. T.8 transitions to the next challenge: finding the right products. The narrative shift is "the system can read emails, now it needs to find the right products." Next up: T.9 will cover LLM re-ranking once hybrid search and filtering are complete.
