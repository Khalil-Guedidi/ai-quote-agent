# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.7 — It's Alive Post
- **Phase:** Email Pipeline (Epic 2)
- **Date drafted:** 2026-03-19

---

## LinkedIn Post

Last week my system processed its first real email. Not a test fixture. Not a hardcoded string. An actual B2B quote request, received, parsed, and structured automatically.

I'm building an AI that handles industrial quote requests. The prototype I built months ago could match products with 96.2% accuracy. Impressive demo. But it couldn't receive an email on its own. It couldn't handle missing data, bad formatting, or someone trying to trick the model. A proof of concept. Nothing you could point at real emails.

So I rebuilt it. Two epics, 14 stories, and a few weeks later, the system now receives emails over IMAP, strips signatures and noise, extracts structured data with an LLM, and splits multi-product requests into individual line items. Four stages, each with its own error handling, each tested independently.

The prototype had zero tests. The production pipeline has 188. The prototype was one monolithic flow. Production is four discrete stages with security layers, log redaction, and graceful degradation at every step.

Here's the honest part: the prototype could match products. The production system can't do that yet. That's the next phase. Different problem, different metrics. But the pipeline is alive. Emails go in, structured data comes out.

At what point did your side project start feeling like a real product?

#BuildInPublic #AI #Milestone #B2B #Python

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 210 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (96.2%, 188 tests, 14 stories, 4 stages, zero tests)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #Milestone #B2B #Python

---

## Series Continuity Note

This is post #7 in the Build in Public series. It follows T.6 (error & edge cases) and closes the Email Pipeline phase (Epic 2). Where T.6 showed how the system handles failures, T.7 marks the milestone: the pipeline actually works end-to-end. Next up: Epic 3, product catalog search.

---

## Contra Project Update

**Epic 2 Complete: Email Processing Pipeline**

The AI quote agent now has a fully functional email processing pipeline. From prototype to production:

- **Pipeline:** 4-stage processing (receive, clean, extract, split) replacing the monolithic n8n prototype flow
- **Quality:** 188 automated tests (up from 0 at prototype), 0 regressions across all 6 Epic 2 stories
- **Security:** 2-layer prompt injection defense, structured logging with confidential data redaction
- **Scale:** 14 stories delivered across 2 epics, 52 Python source files, 5 service modules

**What's next:** Epic 3 brings product catalog search. The system can receive and parse emails. Next it learns to match requests to actual products.
