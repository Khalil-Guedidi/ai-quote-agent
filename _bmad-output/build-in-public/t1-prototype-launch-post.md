# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.1 — Prototype Launch Post
- **Phase:** Launch
- **Date drafted:** 2026-03-17

---

## LinkedIn Post

I'm building an AI agent that reads messy B2B emails and generates quotes in 3 seconds.

I've spent years building AI pipelines in production. They work great — but they don't think. They don't adapt. And they can't say "I'm not sure, let me flag this for a human."

That's what I want to build now. A real AI agent for B2B industrial quoting.

You know the drill if you've worked in distribution: a customer emails "vis M8x40 inox" and someone on the sales team has to figure out that means "stainless steel hex bolt 8mm," find it in the ERP, and draft a quote. Dozens of times a day.

My agent does the whole thing. Email comes in, it understands what the customer wants, searches the product catalog, and creates a draft quote in the ERP. Under 3 seconds.

I prototyped it in n8n to validate the idea fast. First results on a 680-product test catalog:
- 96.2% accuracy finding the right products
- 2.9s per quote on average
- Handles simple, multi-line, and ambiguous requests

The prototype works. Now I'm rebuilding it for real: Python, LangGraph, Qdrant, Claude. A proper agent stack with confidence scoring, memory, and human-in-the-loop routing.

This is post #1. I'm building this in public, start to finish.

If you work in B2B distribution or industrial sales — how much time does your team spend on quoting today?

#BuildInPublic #AI #B2B #SaaS #IndustrialTech

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 228 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #B2B #SaaS #IndustrialTech

---

## Series Continuity Note

This is the FIRST post in the Build in Public series. It establishes the project, the prototype results, and the narrative arc: following the journey from a working prototype to a production-ready AI quoting agent. Future posts will dive into specific technical decisions, challenges, and learnings along the way.
