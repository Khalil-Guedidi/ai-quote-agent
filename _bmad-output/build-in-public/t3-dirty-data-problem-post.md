# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.3 — Dirty Data Problem Post
- **Phase:** Foundation (Epic 1)
- **Date drafted:** 2026-03-18

---

## LinkedIn Post

Everyone talks about AI models. Nobody talks about the data they have to work with.

Here's what a real industrial product catalog looks like. One product: "VIS CHC M8X40 INOX A2". That's a stainless steel hex socket head cap screw. Good luck asking a search engine to find that when a customer writes "M8 stainless screw." Another row has French labels, English specs, and German brand names. Same catalog. And "DN 25", "DN25", "1 pouce", "25mm" all mean the exact same pipe diameter.

This is the data my AI quoting agent needs to search through. No clean descriptions, no consistent formatting. Just thousands of rows of industrial shorthand that human sales reps decode on autopilot.

Most tools need weeks of data cleanup before they work. My bet is the opposite: make the AI adapt to the mess instead of cleaning the mess first.

During prototyping, I tested this on a 680-product catalog that I intentionally left dirty. No cleanup, no restructuring. The system hit 96.2% accuracy on raw, uncleaned data.

The foundation is now in place. Next step: actually ingesting real catalogs and proving this works at scale.

How clean is your product data, really? And how much time does your team spend just maintaining it?

#BuildInPublic #AI #B2B #Data #IndustrialTech

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 208 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #B2B #Data #IndustrialTech

---

## Series Continuity Note

This is post #3 in the Build in Public series. It follows T.2 (stack decision: why the production rewrite moved from n8n to Python/LangGraph). Now that the foundation is in place, this post shifts focus from the "how" to the "what": the messy industrial data that makes this project's core challenge genuinely hard.
