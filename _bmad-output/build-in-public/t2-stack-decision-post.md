# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.2 — Stack Decision Post
- **Phase:** Foundation (Epic 1)
- **Date drafted:** 2026-03-18

---

## LinkedIn Post

My n8n prototype hit 96% accuracy. So naturally, I threw it all away and started over in Python.

Here's why.

n8n was perfect for prototyping. Visual workflows, fast iteration, I had a working AI quoting agent in a few days. But when I started thinking about putting this in production, things got complicated. No tests, no way to handle errors properly, no control over how the agent makes decisions.

So I rebuilt everything from scratch. Python with LangGraph, which basically lets me define exactly how my agent thinks, retries, and routes decisions step by step. A single PostgreSQL database that handles both the product catalog and the vector search (instead of juggling two separate databases). And a proper testing setup from day one.

Two stories in, I already have 21 automated tests and a clean project structure. The prototype had zero of that.

And honestly, that's not a criticism of n8n. It's the tool that helped me validate the idea in days. But prototyping and building for production are two very different games. One rewards speed, the other rewards reliability.

At what point do you decide to stop iterating on something that works "well enough" and start fresh with the right foundations?

#BuildInPublic #AI #Python #LangGraph #B2B

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 207 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #Python #LangGraph #B2B

---

## Series Continuity Note

This is post #2 in the Build in Public series. It follows T.1 (prototype launch results) and explains why the production rewrite uses a completely different stack. T.1 ended with "Now I'm rebuilding it for real" — this post delivers on that promise by explaining the reasoning behind the stack pivot.
