# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.11 — Confidence Tiers Post
- **Phase:** Intelligence (Epic 4)
- **Date drafted:** 2026-03-20

---

## LinkedIn Post

Most AI demos show you the perfect answer. Nobody talks about what happens when the AI isn't sure.

In B2B industrial quoting, a wrong match costs real money. An AI that confidently picks the wrong steel grade is worse than no AI at all. And vague requests are the norm: "something like last time but thicker."

My quote agent now has three levels of certainty. When it finds an exact match ("stainless steel tube 304L DN25"), it scores above 85% confidence and drafts the quote automatically. The sales rep just validates.

When the match is fuzzy ("steel plates for boilermaking"), the score lands between 50% and 85%. The agent shows a few proposals and lets the human choose.

Below 50%? The agent doesn't guess. It tells the sales rep what it understood, what it's unsure about, and what to do next.

Here's what I like about this: the AI gives a confidence score, but simple rules decide what happens. No AI in the decision loop itself. And if something breaks, it defaults to human escalation instead of a wrong quote.

61 new tests, 414 total passing. Still running on synthetic data, not production yet.

When you use an AI tool at work, do you trust it more when it gives you a clear answer, or when it tells you it's not sure?

#BuildInPublic #AI #B2B #Automation

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 213 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (85%, 50%, 414 tests, 61 new tests)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #B2B #Automation

---

## Series Continuity Note

T.10 closed the Search phase with the jargon dictionary story ("I built a feature, benchmarked it, and deleted it"). T.11 opens the Intelligence phase (Epic 4). The system can find products. Now it needs to know how sure it is, and what to do when it isn't. Next: T.12 will cover memory architecture (how the system learns from past decisions).
