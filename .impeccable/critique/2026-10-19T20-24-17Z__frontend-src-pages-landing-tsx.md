---
target: Landing.tsx
total_score: 23
max_score: 36
na_heuristics: 7
p0_count: 0
p1_count: 3
target_identity: "file:/Users/shadielsangedy/Documents/git/packvote/frontend/src/pages/Landing.tsx"
target_fingerprint: "sha256:b0ef71e6289b9dab3d6ee9fa73d49d40242f249822ca64b7b1640d3a6cd70627"
target_path: /Users/shadielsangedy/Documents/git/packvote/frontend/src/pages/Landing.tsx
timestamp: 2026-10-19T20-24-17Z
slug: frontend-src-pages-landing-tsx
---
`⚠️ DEGRADED: no screenshots (plan mode blocks file writes)` · Method: dual-agent (A: design review · B: detector + code audit). Both reviewers worked separately. A took measurements in a live browser at 1440×900 and 390×844, light and dark, but couldn't save images. B's audit comes from the code alone.

## Short answer: animation isn't what's missing

The page already animates: a 180ms fade and an 8px slide-up that nobody notices. Adding scroll-reveal would give you the same flat page, just moving. It feels soulless for four other reasons:

1. **The best idea is never shown.** Instant-runoff settling a group argument is the one thing no competitor has. Here it gets three lines of grey text at the bottom.
2. **The text is set at in-app sizes.** The page uses the same 48/24/14px steps as the dashboard. There's no large headline type, and every h2 is 24px, so "How it works" weighs the same as "Ready to plan?".
3. **Emerald is only a button colour.** With images banned, colour is your main source of atmosphere, and it's spent on four identical CTAs.
4. **The layout is a stock template.** Text on the left with a mock on the right, five equal steps numbered 01–05, a "Ready to plan?" card, identical `gap-20` spacing everywhere. Change "trip" to "sprint" and it's a project-management tool.

Motion earns a place in exactly one spot: **showing the elimination round itself**.

## Design health (Nielsen)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | CTAs switch correctly for signed-in users; little else has state |
| 2 | Real-world match | 2 | "Ranked vote" and "instant-runoff" are explained in jargon; "Join with a code" doesn't say what code |
| 3 | User control | 3 | Nothing traps you; "Plan a trip" lands on /login without saying so |
| 4 | Consistency | 3 | Hero says "decided fairly", footer says "decided together" |
| 5 | Error prevention | 2 | Hero ballot says "Drag the handle, or use the arrows" but is frozen, so drags fail silently |
| 6 | Recognition | 3 | Steps are readable |
| 7 | Flexibility | n/a | No repeat-use paths on a marketing page |
| 8 | Aesthetic/minimal | 2 | Mock is padded with dashboard filler ("6/6 preferences", a date, "Surprise me") |
| 9 | Error recovery | 3 | Almost nothing can fail here |
| 10 | Help | 2 | This page is the only explanation of the voting; ties and non-voters aren't covered |
| **Total** | | **23/36 (64%)** | **Acceptable** |

**Technical audit: 14/20 (Good).** Accessibility 3 · Performance 2 · Theming 4 · Responsive 3 (from code only, not measured) · Implementation integrity 2.

## Design specificity

- **Design review:** generic. The neutrals are stock Tailwind zinc, Geist semibold with tight tracking is the default Vercel look, and the hero frame is three bordered boxes nested inside each other. The travel content is limited to truncated 14px row titles. The sample data does contain good material (the trip code `LISB2026`, "Lisbon, Portugal"), but it never renders, because `optionTitle` prefers `option_title`.
- **Detector:** 0 findings on Landing, Ballot, TripRow and AppShell. That clean result doesn't contradict the design review. The detector catches surface habits such as gradient text or eyebrow labels. The problem here is a lack of decisions, which no rule detects.

## What's working

- **The hero mock reuses the real `Ballot` and `TripRow` components,** so it can't drift from the product. That's a solid starting point for a real demo.
- **Accessibility basics are there:** 44px touch targets, skip link, `inert` plus `aria-hidden` on the mock, accent focus rings, and AA contrast everywhere (muted text is about 7:1 in both themes).
- **"Group trips, decided fairly."** is a specific promise you can defend. Keep it.

## Priority issues

- **[P1] The hero shows a form, not the payoff.**
  - **Fix:** make the hero an instant-runoff tally.
  - **What's in it:** six people as monogram chips, three destination bars, the last-place option eliminated, its votes moving to the voters' next choices, and the winner turning emerald.
  - **How it plays:** once on load, with a Replay button.
  - **Reduced motion:** show the final state plus a small round-by-round table.
  - Command: `/impeccable animate` (the single designed motion moment).
- **[P1] The mock looks clickable but isn't, and it contains a second emerald "Submit ranking" button that competes with "Plan a trip".** Riley will try to drag it and decide the site is broken. Casey on mobile sees two identical green buttons 60px apart.
  - **Fix:** either make it a real local-state demo with no submit button, or render static markup.
  - **Side benefit:** a static version also drops dnd-kit from the landing bundle.
  - Command: `/impeccable distill`
- **[P1] There's no large headline type.**
  - **Fix:** set the h1 to `clamp(3rem, 7vw, 6rem)` and let type stand in for imagery. Destinations go at display size, and the trip code, dates and tallies go in a Geist Mono departures-board treatment.
  - Command: `/impeccable typeset`
- **[P2] Emerald only fills buttons.**
  - **Fix:** use it as data instead: the winner bar, the vote transfers, and one `accent-subtle` band behind the fairness section as the page's colour high point. Allow one primary CTA per screen.
  - Command: `/impeccable colorize`
- **[P2] The story is template copy.**
  - **Fix:**
    - Open on the pain point (e.g. "143 messages. 0 decisions.").
    - Cut the steps to three: Invite → Everyone ranks → Fair winner.
    - Make fairness the high point, with a small FAQ on ties and non-voters.
    - End on something concrete: "Your friends don't need an account."
  - Command: `/impeccable clarify`

## Technical findings (audit)

- **[P2] Empty grid cell between 640 and 1023px.** The 5-step grid is `sm:grid-cols-2`, so the last row leaves an empty cell, which shows as a solid grey block (`Landing.tsx:136`). Found from the code; not seen in a browser.
- **[P2] The landing loads everything.** It ships all of dnd-kit, base-ui Dialog (via OptionCard) and every route, since there's no `React.lazy` in `App.tsx:4-11`. Google Fonts load 6 weights and block rendering, and Geist Mono is used only for the step numbers.
- **[P2] The hero hides real buttons using only `inert`** (one Link plus 10 buttons). If `inert` were ever dropped, focusable content would be inside an `aria-hidden` block.
- **[P3]**
  - The secondary CTA's border is 1.27:1 against its background, so it barely reads as a button.
  - The h1 starts at opacity 0, which delays the largest paint slightly.
  - The "PackVote" brand link is about 24px tall.
  - The section ids are generic (`hero`, `how`).
- **The current motion handling is fine.** The global `prefers-reduced-motion` rule shortens all animations to 0.01ms (styles.css:109), which is enough for today's fades. A runoff demo will need its own reduced-motion version, because cutting it to 0.01ms would just jump to the end.

## Persona red flags

- **Jordan (first-timer):** "instant-runoff" with no picture, "Join with a code" with no context, "guests need no account" buried in 14px step text, and "Surprise me" in the mock looks like a bug.
- **Riley (stress tester):** drags the ballot and nothing happens, clicks Submit and nothing happens, finds no answers on ties or abstentions, and the tab title is just "PackVote".
- **Casey (mobile, one-handed):** the CTAs are at the top of the screen (y≈317) with nothing reachable lower down, there's about 780px of stacked steps, and the two CTAs sit side by side at the same height, which invites mis-taps.

## Minor observations

- The nested borders in the hero frame are three levels deep.
- Every section gap is identical, so the page has no rhythm.
- The meta description ("AI-powered group travel planning") is generic.
- In dark mode the rank-1 chip and every primary button share `#34d399`, so the accent no longer signals anything.

## Questions to consider

- Do people choose PackVote for the AI, or because it ends the group-chat argument? Right now the copy leads with neither.
- What if a visitor could reorder a friend's ballot in the hero and watch Lisbon lose?
- With no images allowed, could the whole page be a departures board?

The `.impeccable/critique/` snapshot and trend line were skipped because plan mode blocks writes, so this is effectively the first run for this target.
