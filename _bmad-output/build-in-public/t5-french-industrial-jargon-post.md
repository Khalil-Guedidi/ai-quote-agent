# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.5 — French Industrial Jargon Post
- **Phase:** Email Pipeline (Epic 2)
- **Date drafted:** 2026-03-19

---

## LinkedIn Post

"50 vannes papillon DN100 en inox 316L." That's an entire product request. It's also completely unreadable if you don't work in French industrial supply.

I'm building an AI that processes B2B quote request emails. The first real challenge? Cleaning them. Every email comes buried in reply threads, legal disclaimers, and signatures. You need to strip all that noise. But here's the catch: the most important data in the email looks exactly like noise to a generic parser.

DN100 means pipe diameter. PN16 is a pressure rating. Inox 316L is a stainless steel alloy. Vannes papillon are butterfly valves. Ø means diameter, lg means length. These abbreviations ARE the request. Remove them and you have nothing left to quote.

So I built a 4-stage cleaning pipeline that knows the difference between "Cordialement, Sophie" (a signature, strip it) and "DN50--PN16 en acier" (a product spec, keep it). It handles French and English patterns. And if the cleaner ever strips more than 90% of the content, a safety valve kicks in and returns the original. Because over-cleaning is worse than no cleaning at all.

18 tests just for this cleaning step. Because when you're deciding what to keep and what to throw away, you better be right.

What's the weirdest abbreviation your industry uses that outsiders would never understand?

#BuildInPublic #AI #NLP #B2B #IndustrialTech

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 210 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (4-stage pipeline, 90% safety valve, 18 tests)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #NLP #B2B #IndustrialTech

---

## Series Continuity Note

This is post #5 in the Build in Public series. It follows T.4 (foundation recap) and marks the transition into the Email Pipeline phase (Epic 2). The series moves from "building the foundation" to "tackling the real domain challenge": processing French industrial emails where the most valuable data looks like gibberish.
