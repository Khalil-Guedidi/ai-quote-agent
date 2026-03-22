# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.13 — Intelligence Recap Post
- **Phase:** Intelligence (Epic 4)
- **Date drafted:** 2026-03-22

---

## LinkedIn Post

Four months ago, my AI quote agent could find the right product in a catalog of 50,000 references. But finding the right product was only step one. A sales rep still had to figure out what to do with the match.

In B2B industrial quoting, the gap between "here's a product" and "here's a quote" is where most automation breaks down. Vague requests, compliance requirements, uncertain matches. You can't just auto-generate a quote every time.

So I built a 7-step pipeline. An email arrives. The agent classifies the request by complexity. It searches products, scores its own confidence, reviews its own work, checks export compliance, and creates a draft quote in the ERP. Every step has one rule: if something goes wrong, ask a human. No step ever approves by default.

I also built a jargon dictionary for industrial abbreviations, benchmarked it, and deleted it. 96% accuracy with the dictionary, 96% without. The AI model already understood the jargon. (I shared that story a few posts back.)

11 stories completed. 243 new tests (599 total), zero regressions. 9 CLI commands so every step is visible from the terminal.

The agent can now think. Next step: making sure the right human sees the result at the right time.

When you automate a process, do you start by defining what happens when it works, or what happens when it fails?

#BuildInPublic #AI #B2B #Automation #LLM

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 218 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (50,000, 96%, 243, 599, 11, 9)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #B2B #Automation #LLM

---

## Series Continuity Note

T.11 opened the Intelligence phase with confidence tiers (how the agent knows when it's sure vs. when it needs help). T.13 closes the entire phase by zooming out: the system now has a complete 7-step reasoning pipeline. The jargon dictionary callback ties to T.10's "build, benchmark, delete" theme. Next: T.14 will cover human-AI collaboration (notifications, the human loop).

---

## Contra Project Update

**Epic 4 Complete: Adaptive Reasoning & Quote Generation**

The AI quote agent now has a full reasoning pipeline from email to draft quote:

- **Pipeline:** 7-step agent (classify, search, score, reason, self-review, compliance, draft) orchestrated by LangGraph
- **Quality:** 599 automated tests (up from 363 at Epic 3), 11/11 stories delivered, 0 regressions
- **Safety:** Fail-safe by default on all 7 nodes. Errors trigger escalation or rejection, never approval
- **CLI:** 9 commands providing full pipeline visibility (`search`, `classify`, `reason`, `score`, `review`, `compliance`, `erp-read`, `draft-create`, `process`)
- **Data-driven:** Jargon dictionary built, benchmarked (96% vs 96%), and removed. Zero-preprocessing vision preserved
- **Compliance:** Export control and sanctioned entity detection integrated before quote generation

**What's next:** Epic 5 brings notifications and the human workflow. The agent creates drafts. Now the right person needs to see them at the right time.
