# Content Guidelines — Build in Public Series

## Tone & Voice

- **Technical but accessible:** Write for engineers who might not be in your exact niche. Explain domain-specific terms (e.g., "Hit@5" or "hybrid search") briefly when first used.
- **Authentic and conversational:** Write like you're explaining to a smart colleague over coffee. First person, active voice, short sentences.
- **Not corporate:** No "leveraging synergies" or "driving value." Say what you mean directly.
- **Confident but honest:** Share what worked AND what didn't. Uncertainty is fine — "I'm not sure this will scale, but here's what the data shows so far."
- **Problem-first:** Always start from a real problem, not from the technology. The reader should care about the problem before you introduce your solution.

## Structure

Every post follows this flow:

1. **Hook** — A surprising result, counterintuitive finding, or provocative question
2. **Problem** — The real-world B2B industrial challenge being solved
3. **Solution / Insight** — What you built or learned, at a technical-but-accessible level
4. **Metric / Proof** — At least one concrete number (accuracy, latency, coverage, cost)
5. **Open Question / CTA** — A genuine question or invitation to discuss

This structure ensures each post delivers value and invites engagement.

## Rules

### Language
- All posts in **English**
- Technical terms in English (no translation needed for industry-standard terms)

### Confidentiality
- **Never** mention past clients by name
- **Never** share confidential information from previous work
- All examples use **synthetic data only** from this repo
- Frame professional experience as **domain expertise**: "After working on B2B industrial quoting systems..." not "When I worked for Company X..."

### Data Integrity
- All metrics must come from this repo's code, benchmarks, and test results
- Always cite the source context (which story, which benchmark, which test)
- Don't exaggerate results — if something is a prototype metric on synthetic data, say so

### Content Scope
- Each post is tied to a specific story milestone (T.1–T.15)
- Each post stands alone (new readers can follow) but builds on previous ones
- Reference previous posts when relevant: "In my last post, I showed..."

## Posting Cadence

- **Target:** 1 post per week
- **Aligned to:** story milestones — each post corresponds to a completed story or meaningful milestone
- **Flexibility:** Skip a week if no meaningful milestone was reached. Quality over frequency.
- **Best times:** Tuesday–Thursday, morning (LinkedIn algorithm favors mid-week posts)

## Series Narrative Arc

The content follows the project's development phases:

| Phase | Stories | Theme | Key Angle |
|-------|---------|-------|-----------|
| **Launch** | T.1 | Prototype results announcement | "Here's what I built in a weekend" |
| **Foundation** (Epic 1) | T.2–T.4 | Stack decisions, dirty data, infrastructure | Technical decision-making process |
| **Email Pipeline** (Epic 2) | T.5–T.7 | French jargon, edge cases, first real email | NLP challenges in non-English B2B |
| **Search** (Epic 3) | T.8–T.10 | Hybrid search, LLM reranking, search recap | Search architecture deep dives |
| **Intelligence** (Epic 4) | T.11–T.13 | Confidence tiers, memory, reasoning | AI reasoning and trust calibration |
| **Full Loop** (Epic 5) | T.14–T.15 | Human-AI collaboration, retrospective | Lessons learned, what's next |

Each phase builds audience trust: prototype proof → technical depth → real-world challenges → intelligent systems → human-AI collaboration.

## Hashtag Strategy

Use 3–5 hashtags per post. Core set + 1–2 topic-specific:

**Core (always include):**
- #BuildInPublic
- #AI

**Rotate based on topic:**
- #LLM, #NLP, #VectorSearch, #RAG (technical topics)
- #B2B, #SaaS, #IndustrialTech (domain topics)
- #Python, #LangGraph, #OpenAI (stack topics)
- #SoloFounder, #IndieHacker (community topics)

## Quality Checklist (before publishing)

- [ ] Does it start with something interesting? (Would I stop scrolling?)
- [ ] Is there a specific, real problem being addressed?
- [ ] Does it include at least one concrete metric or result?
- [ ] Is it 150–250 words?
- [ ] No client names, no confidential info?
- [ ] All data from this repo only?
- [ ] Does it end with a genuine question?
- [ ] Would I enjoy reading this if someone else wrote it?
