# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.9 — LLM Re-ranking Post
- **Phase:** Search (Epic 3)
- **Date drafted:** 2026-03-20

---

## LinkedIn Post

Vector search found the right product. It also found 200 you can't actually sell.

Last post, I shared how I built the search foundation: 50,000 products indexed with vector embeddings so the system understands meaning, not just keywords. It worked. But "working" in a demo and "working" in production are two very different things.

Three problems showed up fast. First, vector search alone misses exact product codes. A customer types "TUB-304L-025" and semantic search tries to interpret the meaning instead of just finding the exact match. Second, the results include discontinued and out-of-stock products. Finding the right product doesn't help if you can't sell it. Third, industry shorthand like "inox DN100" means nothing to the search engine without knowing that "inox" means stainless steel and "DN" means nominal diameter.

So I added three layers on top. A hybrid search that combines meaning and keywords, then picks the best results from both. A filter that removes unsellable products before they even reach the results. And a jargon dictionary that automatically expands abbreviations into full terms.

The result: 363 tests passing, search under 3 seconds on 50,000 products, and repeated searches return in under 1 second from cache.

When you search for a product at work, how often does the system actually understand what you mean?

#BuildInPublic #AI #Search #B2B #Python

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 212 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (363 tests, 3 seconds, 50,000 products, 200, 1 second)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #Search #B2B #Python

---

## Series Continuity Note

This is post #9 in the Build in Public series, continuing the Search phase (Epic 3). T.8 covered the search foundation (vector embeddings, pgvector, multilingual model). T.9 answers "and then what?" by showing the three layers that made search production-ready. Next: T.10 will wrap up the full search story after Epic 3 is complete.
