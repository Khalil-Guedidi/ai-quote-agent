# LinkedIn Post Draft — Build in Public Series

## Post Metadata

- **Story:** T.6 — Error & Edge Cases Post
- **Phase:** Email Pipeline (Epic 2)
- **Date drafted:** 2026-03-19

---

## LinkedIn Post

Every AI demo shows the happy path. The model gets a clean input, produces a perfect output, and everyone claps. But production is not a demo.

I'm building an AI that turns B2B quote request emails into structured data. Sometimes the email is empty. Sometimes the model takes 15 seconds to respond. Sometimes the extraction returns a product with no quantity, no reference, just a vague description. What happens then?

You plan for it. Every failure gets a strategy.

If the model takes too long, a 10-second timeout kills the call and raises a clean error. If the extraction fails on one email, that email gets flagged and the pipeline moves to the next one. If the model can't find a quantity, the field stays empty. No guessing. No hallucinated data. If the splitting step fails entirely, the system falls back to treating everything as one single request. The pipeline keeps moving.

And for each of these decisions, there's a test. 166 of them so far. Because the happy path is maybe 10% of the code. The other 90%? Making sure the system survives the real world.

When you ship an AI feature, what's your plan for when the model just... doesn't work?

#BuildInPublic #AI #Engineering #Reliability #B2B

---

## Formatting Checklist

- [x] Total length: ~150-250 words (approx. 207 words)
- [x] Written in English
- [x] No past client names or confidential information
- [x] All data comes from this repo's code, synthetic data, and metrics
- [x] Professional experience framed as domain expertise, not client work
- [x] Includes at least one concrete number or metric (10-second timeout, 166 tests, 10%/90% ratio)
- [x] Ends with a question or conversation starter
- [x] No corporate buzzwords — keep it authentic and conversational
- [x] Hashtags (3-5 max): #BuildInPublic #AI #Engineering #Reliability #B2B

---

## Series Continuity Note

This is post #6 in the Build in Public series. It follows T.5 (French industrial jargon) and continues the Email Pipeline phase. Where T.5 showed the challenge of understanding domain-specific language, T.6 shifts to what happens when the processing pipeline hits a wall.
