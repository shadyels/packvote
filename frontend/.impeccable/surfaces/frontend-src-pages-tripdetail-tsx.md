---
version: 1
slug: "frontend-src-pages-tripdetail-tsx"
primary_target: "frontend/src/pages/TripDetail.tsx"
related_targets:
  [
    "frontend/src/pages/Dashboard.tsx",
    "frontend/src/pages/Trip.tsx",
    "frontend/src/pages/Join.tsx",
    "frontend/src/pages/Login.tsx",
    "frontend/src/pages/ResetPassword.tsx",
    "frontend/src/pages/NotFound.tsx",
  ]
---

## Direction contract

MODE: Operate. The visitor completes a task: create and track trips, submit preferences, rank options, read and finalize the result.

THESIS: Every trip is a departure. The trip code sits in split-flap tiles beside a solid status flap, a gate strip shows where the trip is in its lifecycle, the dashboard is a departures board of the user's trips, and Results is the real round-by-round runoff board. It refuses stacked rounded bordered cards, pale pill badges, grey bar-chart results and the generic text-2xl-h1 app kit.

OWN-WORLD: Inherited from frontend/DESIGN.md ("The Departures Hall"); this surface extends it, never replaces it. Status flaps use product words: CREATED / COLLECTING (muted), GENERATING (warning), FAILED (danger), VOTING (flap, near-black so it never competes with the yellow primary), FINALIZED (success). BOARDING, ELIMINATED, RUNNER-UP and TIED appear only on the results board. Tone steps and 2px foreground top rules separate sections instead of boxes. Geist for type; Geist Mono for codes, counts, statuses and dt labels.

STORY: The organizer opens My trips, scans a board of departures, opens one, sees exactly which gate it is at and the single next action; guests follow an emailed link, submit preferences, rank options and watch the board resolve to BOARDING.

FIRST VIEWPORT: Trip screens: h1 with the trip code (or the guest's destination) in board-size flap tiles and the gate strip directly below, then the one primary action for the current stage. Dashboard: h1 "My trips", the single "New trip" primary, the tabs, then the trip board. App-scale type, no hero.

MOTION: State changes only. Flaps flip when a value changes after mount; ballot rows FLIP into place on reorder; the results board plays the runoff once and offers Replay; the tab underline slides. Nothing animates on page load. Under reduced motion everything shows its final state.

FORM: Departures board (inherited from the landing). seed: none (world inherited from the landing surface; roll skipped)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md extended with the new components
