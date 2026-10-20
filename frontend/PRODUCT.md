# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Organizer:** the friend who ends up planning the group trip. Has an account (email + password), creates the trip, invites the group, triggers itinerary generation and finalizes the winner.
- **Participants:** the rest of the group. They need no account: they arrive through an emailed invitation link, or join with the trip code and PIN, then submit preferences and rank the options.

## Product Purpose

PackVote turns a group's scattered preferences into one agreed trip. The organizer collects everyone's preferences, AI drafts itinerary options from the whole group's input, and the group settles it with a ranked vote. Success is a finalized trip the group accepts without a group-chat argument.

## Positioning

The decision is made by instant-runoff (ranked-choice) voting, not by whoever shouts loudest or a plurality poll: if no option has a majority, the last-place option is eliminated and its voters' next choices count, until one option wins. The leader on first preferences can lose to the option the group as a whole prefers.

## Operating Context

- Trip lifecycle: create → invite by email → collect preferences → AI generates options → vote → organizer finalizes; the group is notified by email at key steps.
- Participants are typically on phones, following an emailed link.
- Results are computed from the ballots on every read; nothing is stored as a tally.

## Capabilities and Constraints

- AI runs on an OpenAI-compatible endpoint (currently a free-tier Gemini model) with strict rate limits; generation is asynchronous and can fail.
- Email goes through Brevo's free tier (300 emails/day).
- Web app (React + Vite), fully mobile-responsive, light and dark themes following the OS setting with no toggle.

## Brand Commitments

- Name: PackVote.
- Promise line: "Group trips, decided fairly."
- No photography or imagery anywhere in the product.

## Evidence on Hand

None. There are no testimonials, user counts, customer logos, press or benchmarks. Future work must not fabricate them; any sample trip shown must be labeled as a sample.

## Product Principles

1. Fairness is the product: show the mechanism, never just assert it.
2. Guests carry no burden: no account, minimal steps, works on a phone.
3. The organizer stays in control: AI drafts, the group decides, the organizer finalizes.
4. Claims stay true to the shipped behavior.
