---
name: PackVote
description: Group trips, decided fairly.
colors:
  signal-yellow: "#ffc81e"
  concrete: "#e9ecef"
  sign-white: "#ffffff"
  concrete-muted: "#dde1e6"
  sign-black: "#0e1116"
  slate-text: "#4a5260"
  concrete-rule: "#c9ced6"
  boarding-green: "#13723f"
  eliminated-red: "#b42318"
  eliminated-red-subtle: "#fdecea"
  warning-orange: "#b4370a"
  flap-ink: "#f4f5f7"
  board-night: "#0b0f17"
  board-panel: "#141a24"
  board-muted: "#1c2330"
  board-white: "#edeff2"
  board-slate-text: "#9aa3b2"
  board-rule: "#2a3343"
  board-green: "#4ade80"
  board-red: "#f87171"
  board-orange: "#fb923c"
  board-flap: "#05070b"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3rem, 7vw, 6rem)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "3rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
  label:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
    letterSpacing: "0.05em"
  flap:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.4
  cell-label:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.7rem"
    fontWeight: 400
rounded:
  flap: "4px"
  control: "8px"
  card: "12px"
  panel: "16px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  section: "96px"
components:
  button-primary:
    backgroundColor: "{colors.signal-yellow}"
    textColor: "{colors.sign-black}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.sign-white}"
    textColor: "{colors.sign-black}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.concrete-muted}"
  button-ghost:
    textColor: "{colors.sign-black}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "36px"
  button-ghost-hover:
    backgroundColor: "{colors.concrete-muted}"
  button-danger:
    backgroundColor: "{colors.eliminated-red}"
    textColor: "{colors.sign-white}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "44px"
  input:
    backgroundColor: "{colors.sign-white}"
    textColor: "{colors.sign-black}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "44px"
  card:
    backgroundColor: "{colors.sign-white}"
    rounded: "{rounded.card}"
    padding: "16px"
  flap-tile:
    backgroundColor: "{colors.sign-black}"
    textColor: "{colors.flap-ink}"
    typography: "{typography.flap}"
    rounded: "{rounded.flap}"
    width: "32px"
    height: "44px"
  flap-tile-sm:
    backgroundColor: "{colors.sign-black}"
    textColor: "{colors.flap-ink}"
    rounded: "{rounded.flap}"
    width: "20px"
    height: "28px"
  status-flap-muted:
    backgroundColor: "{colors.concrete-muted}"
    textColor: "{colors.slate-text}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  status-flap-flap:
    backgroundColor: "{colors.sign-black}"
    textColor: "{colors.flap-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  status-flap-warning:
    backgroundColor: "{colors.warning-orange}"
    textColor: "{colors.concrete}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  status-flap-success:
    backgroundColor: "{colors.boarding-green}"
    textColor: "{colors.concrete}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  status-flap-danger:
    backgroundColor: "{colors.eliminated-red}"
    textColor: "{colors.concrete}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  tab-active:
    textColor: "{colors.sign-black}"
    height: "44px"
    padding: "0 8px"
---

# Design System: PackVote

## Overview

**Creative North Star: "The Departures Hall"**

PackVote borrows the two faces of an airport. Dark mode is the departures board: a blue-black ground, near-black split-flap cells, cool-white type and one signal yellow. Light mode is the wayfinding sign: cool concrete grey, solid yellow panels, black type. Both themes follow `prefers-color-scheme`, and there is no toggle. Both read as public, legible information rather than decoration. The group's vote is shown as a board resolving, with flaps turning and a row going to BOARDING, not as a chart.

Density is calm. A single centred column (64rem) holds generous section gaps. Type is large and tight-tracked for statements, and monospaced for data: codes, counts, statuses. Depth comes from tone and hairline rules, not shadows. Motion is mechanical and short: tiles flip down into place, and chips slide to their new row with a long ease-out. On the app screens motion answers a state change and nothing plays on page load, apart from the generating indicator's pulse.

The product rule "no photography or imagery anywhere" holds visually too: there are no rasters, illustrations or hero images. The board, type and yellow carry the identity.

**Key Characteristics:**

- Two themes, one world: departures board (dark) and wayfinding sign (light).
- Signal yellow is the only accent, used sparingly and on purpose.
- Geist for statements, Geist Mono for anything a board would print.
- Flat, rule-separated surfaces. Shadows only on lifted interaction states.
- Status is a solid split-flap, read the way an airport reads it: green = boarding/winner, red = eliminated/failed, near-black = voting.

## Colors

The palette is cool, blue-grey neutrals with one hot signal yellow and two status colors. Frontmatter keys prefixed `board-` are the dark-theme values of the same semantic roles. The app consumes them through `--color-*` custom properties in `src/styles.css`, so components never pick a theme by hand.

### Primary

- **Signal Yellow** (`signal-yellow`, both themes): the only accent. It fills the primary button, the "fair winner" panel, the BOARDING row on the board, and text selection. Text on it is always the foreground near-black (`--color-accent-foreground`).

### Secondary

- **Boarding Green** (`boarding-green` light / `board-green` dark): success: the winner, BOARDING, FINALIZED, Submitted. Solid fill for status flaps, and the winning option card's border.
- **Eliminated Red** (`eliminated-red` light / `board-red` dark): danger: elimination, FAILED and destructive actions. Solid fill for status flaps. Its subtle tint (`eliminated-red-subtle`) backs inline form error alerts, with red text on it.

### Tertiary

- **Warning Orange** (`warning-orange` light / `board-orange` dark): warnings only, including the GENERATING flap and the generating indicator. It is deliberately burnt so it never reads as the yellow accent.

### Neutral

- **Concrete** (`concrete`) / **Board Night** (`board-night`): page background.
- **Sign White** (`sign-white`) / **Board Panel** (`board-panel`): surfaces: cards, the board, inputs, the secondary button.
- **Concrete Muted** (`concrete-muted`) / **Board Muted** (`board-muted`): table header band, voter chips, muted status flaps, hover fills.
- **Sign Black** (`sign-black`) / **Board White** (`board-white`): foreground text.
- **Slate Text** (`slate-text`) / **Board Slate Text** (`board-slate-text`): secondary text, captions, inactive tabs and nav.
- **Concrete Rule** (`concrete-rule`) / **Board Rule** (`board-rule`): every border and divider (it is the global default border color).
- **Flap** (`sign-black` light / `board-flap` dark) with **Flap Ink** (`flap-ink` / `board-white`): split-flap letter tiles and the VOTING / Leading status flap. They are near-black in both themes and carry a faint white inset edge (`#ffffff1a`) in dark only.

### Named Rules

**The Fill-Only Yellow Rule.** In light mode yellow is only ever a fill. Text, focus rings, caret, active-tab underlines and accent arrows use `--color-accent-ink`, which is sign black in light and signal yellow in dark. Never put yellow text or a yellow stroke on a light surface.

**The One Yellow Primary Rule.** Exactly one yellow primary action per screen. Secondary navigation that duplicates it (for example the header "Sign in") is a text link, not a button.

**The Solid Status Rule.** Status labels are solid fills with their own text color (green BOARDING, red ELIMINATED, muted RUNNER-UP), so they stay legible on the yellow winner row in both themes. Green or red text on yellow fails in dark and is not allowed.

**The Yellow Means Final Rule.** On the results board the yellow row belongs to the trip that is boarding. Until the trip is finalized the leader reads LEADING on a near-black flap and no row is yellow.

**The Contrast Floor Rule.** Text holds at least 4.5:1 on background, surface and muted, and rings and non-text UI hold at least 3:1, in both themes. A new color pairing has to meet this before it ships.

## Typography

**Display Font:** Geist (with ui-sans-serif, system-ui)
**Body Font:** Geist
**Label/Mono Font:** Geist Mono (with ui-monospace, SFMono-Regular, Menlo)

**Character:** A neutral grotesk set big and tight for plain-spoken statements, paired with a monospace that prints data the way a departures board does. Both load from Google Fonts (Geist 400–700, Geist Mono 400–500). Body text enables `calt` and `kern`.

### Hierarchy

- **Display** (600, clamp(3rem, 7vw, 6rem), 0.98): the page's one statement h1, full width, `text-wrap: balance`.
- **Headline** (600, 1.875rem stepping to 3rem from 640px, tight): statement h2s inside feature panels.
- **Title** (600, 1.5rem, tight tracking): section h2s. Card and step titles step down to 1.125rem / 1rem.
- **Body** (400, 1rem; lede 1.125rem; supporting 0.875rem): prose and descriptions. Ledes cap at about 48rem (`max-w-3xl`), panel prose at 42rem.
- **Label** (Geist Mono 500, 0.75rem, 0.05em, uppercase): board column headers and status flaps. Tabular figures on all counts.
- **Flap** (Geist Mono 500, uppercase, 0.875rem → 1rem at 768px → 1.25rem at 1024px): one letter per split-flap tile. Small tiles (trip codes in lists, ballot ranks) stay at 0.875rem.
- **Cell label** (Geist Mono 400, 0.7rem, 70% opacity): the column name (R1, R2) printed before a count on the stacked mobile boards, where the header band is hidden. Both the landing board and the results board use it.

### Named Rules

**The Board Prints Mono Rule.** Anything a board would print (destination codes, initials, vote counts, statuses, trip codes and PINs) is Geist Mono with tabular numerals. Prose, headings and buttons are never mono.

## Layout

The page is a single centred column, `max-width: 64rem`, with 16px side padding and a sticky 56px header (background at 90% opacity with backdrop blur). Sections stack vertically with large, stepped gaps: 64–80px on mobile, 96–112px from 640px. Inside sections, the rhythm runs on 4/8/12/20/24px gaps.

The board is the hero object at full content width, never a side card. It responds in three steps. Below 768px each row is a stacked grid (name across the top, voters and counts on the second line, status on the third) and the column headers are visually hidden. From 768px (`md`) it is a real table. From 1024px (`lg`) the tiles grow to 32×44px and the R1/R2/Status columns take fixed widths (7rem, 7rem, 11rem).

The trip-list board and the results board follow the same pattern: a real table from 768px, stacked rows with a visually hidden header below it.

Step sequences run horizontally from 640px, with accent-ink arrows between steps, and vertically below it with down arrows. Every interactive target is at least 44px tall. Small buttons grow to 44px on coarse pointers.

## Elevation & Depth

The system is flat. Surfaces separate by tone (concrete → white, or night → panel) and by 1px rules in the border color. Section breaks use a 2px foreground top rule: over step columns, app-screen sections, empty states and the generating state. The tab strip's 1px base rule is drawn as an inset box-shadow (`inset 0 -1px 0` border color) so the active indicator can sit over it inside a horizontally scrolling strip; it is a rule, not depth. The only shadows are interaction states: a dragged ballot row lifts, and the mobile bottom-sheet dialog sits over a scrim (`--color-overlay`).

### Shadow Vocabulary

- **Lifted drag** (Tailwind `shadow-lg` plus a 1px accent-ink ring): a ballot row while it is being dragged.
- **Sheet** (Tailwind `shadow-xl`): the dialog popup over the overlay.

### Named Rules

**The Flat-At-Rest Rule.** Nothing casts a shadow at rest. Depth appears only when the user picks something up or opens something over the page.

## Shapes

Corners scale with the size of the object. Split-flap tiles, status flaps, voter chips and the board frame use 4px corners, which reads mechanical. Buttons and inputs use 8px. Cards and ballot rows use 12px. The yellow feature panel and the guest winner panel use 16px, as does the top edge of the bottom-sheet dialog. The generating indicator's bars are the only fully rounded shapes. Each flap tile is split by a 1px horizontal midline (black at 60%), the one decorative geometry in the system and the mark of a split-flap cell.

## Components

### Buttons

Direct and tactile. Each press nudges the button down to 98% scale.

- **Shape:** gently rounded (8px).
- **Primary:** signal-yellow fill, foreground text, 44px tall, 16px horizontal padding, medium 0.875rem label. Hover darkens slightly (`brightness(0.95)`).
- **Secondary:** surface fill with a 1px slate border; hover fills muted.
- **Ghost:** text only, 36px (44px on coarse pointers); hover fills muted. Used for in-board actions such as Replay and for Log out.
- **Danger:** red fill with surface text; hover drops to 90% opacity.
- **Focus:** the global 2px accent-ink outline at 2px offset. Inside the yellow panel it switches to the foreground color.
- **Disabled / loading:** 50% opacity. Loading shows a spinner and keeps the button's width.

### Chips

- **Voter chips:** 24px (28px from 768px) mono initials on muted, 4px corners. On the winner row they invert to near-black with yellow text.

### Status Flaps

Status is never a pill. It is a solid split-flap: 28px tall, 4px corners, 8px horizontal padding, Geist Mono 0.75rem medium, uppercase and tracked. Five tones, each a solid fill with its own text color:

- **Muted** (muted fill, slate text): CREATED, COLLECTING, Pending, and on the results board RUNNER-UP, TIED and WON VOTE.
- **Flap** (near-black flap fill, flap ink, dark-mode edge ring): VOTING, and LEADING on the results board. It is near-black so it never competes with the yellow primary.
- **Warning** (orange fill, background-color text): GENERATING.
- **Danger** (red fill, background-color text): FAILED, ELIMINATED.
- **Success** (green fill, background-color text): FINALIZED, BOARDING, Winner, Submitted.

Trip statuses come from one table (`STATUS` in `lib/trip.ts`), so the dashboard, trip header and guest view always print the same word in the same tone. BOARDING, ELIMINATED, RUNNER-UP, TIED, LEADING and WON VOTE appear only on the results board.

### Split-Flap Words

Any word a board would print (trip codes, ballot ranks, destinations, option names) is a row of tiles, one character each. Two sizes: small (20×28px) for trip codes in lists and ballot ranks, and board (20×28px stepping to 24×36px at 768px and 32×44px at 1024px) for headers and boards. Long names are cut to their part before the first comma and capped at 12 characters (11 on the guest winner panel, to fit 320px). Inverted tiles (yellow text on near-black) sit on yellow rows and panels. The first paint never animates; only tiles whose character changes after mount flip. The tiles are `aria-hidden` and the full text goes to a screen-reader label.

### Trip Header

The trip screen's first viewport. A 1.5rem h1 (1.875rem from 640px) with an optional slate subline sits on the left. On the right is the trip code in board-size flap tiles with a small copy icon, the whole thing one 44px button that copies the code. Guests see their destination in board tiles instead, or "Destination TBD" in slate text. Below 640px the code drops under the title. The gate strip sits directly below.

### Gate Strip

The trip's lifecycle as four gates: Collecting, Generating, Voting, Finalized. Each gate is a column with a top rule. Passed gates get a 2px foreground rule. Upcoming gates get a 1px rule and slate mono labels. The current gate gets a 2px rule (red when generation failed) and the trip's status flap in place of its label. Below 640px only the current gate keeps a visible label; the others are screen-reader text with "(done)" or "(upcoming)". The current flap flips only when the status changes after mount.

### Trip-List Board

The dashboard lists trips as a departures board, in the same frame as the landing board: surface, 4px corners, 1px rule, a muted mono header band (Trip, Code, Prefs, Status). Each row shows the title and destination, the trip code in small flap tiles, a mono `submitted/total` preferences count and the status flap. The title link is stretched over the whole row, so the row is one target. Hover and keyboard focus fill the row muted, and focus adds a 2px accent-ink outline inset on the row. Below 768px the header is visually hidden and each row is a two-column grid: title and count on the first line, code and status on the second. Loading shows the header band over three skeleton rows.

### Results Board (signature)

The real round-by-round runoff, in the landing board's frame. A mono caption ("N ballots · Iteration N") sits above the header band (Option, R1…Rn, Status). Each row is an option: its name in board-size flap tiles with the full title beneath (screen-reader only when it matches the tiles), a mono count per round, and a status flap. An option that was already out shows "–" in place of a count.

- **Live (not finalized):** the vote's leader reads LEADING on a near-black flap. No row is yellow. A tie with no winner reads TIED, muted.
- **Finalized:** the winner's row fills yellow with inverted tiles and reads BOARDING. Others read RUNNER-UP (muted) or ELIMINATED (red).
- **Organizer override:** when the organizer finalizes an option other than the vote's winner, the organizer's pick gets BOARDING and the yellow row, the vote's winner reads WON VOTE (muted, no yellow), and an "Organizer finalized {title}" line sits above the board.
- **Empty:** with no ballots yet, the board is replaced by the empty state.

The board renders settled on mount. It plays the runoff when the rounds change after mount, when the user presses Replay, or on mount when the user reached it by switching tabs. Each phase is 650ms: a round's counts flip in, then that round's elimination flips to ELIMINATED, and after the last round the status flaps and the yellow row land. Content not yet revealed is faded, never removed. A ghost Replay button sits under the board and is hidden under reduced motion. Below 768px rows stack: the name across the full width, the counts in a line with their cell labels, the status below.

### Ballot

A ranked list of rows. Each row is a 12px-corner surface row with a 1px rule: a drag handle, the rank as a small flap tile, the option title with a slate "N days · budget" line in tabular figures, and up/down arrow buttons, all 44px targets. A move by arrow slides the rows to their new places with a 300ms FLIP (`element.animate`) and keeps focus on the moved row's arrow. Changed rank digits flip. A dragged row lifts (see Elevation).

### Cards / Containers

- **Corner Style:** 12px.
- **Background:** surface on the page background.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px rule. The winning option gets a success-green border and a green Winner status flap. Dimmed options drop to 60% opacity.
- **Internal Padding:** 16px.
- **Content:** highlights are one slate line joined with " · ", not tags.

Option cards and ballot rows are the one deliberate exception to the app screens' refusal of stacked rounded bordered cards: options carry enough prose to need a container, and ballot rows are things the user picks up and moves. Everything else on the app screens separates by tone and 2px top rules.

### Empty State

A 2px foreground top rule over a 1rem semibold heading and one line of slate text (max 65ch). No icon, no box, no illustration. The generating state uses the same rule (red when generation failed) over a row of pulsing orange bars, a heading and a rotating tip.

### Inputs / Fields

- **Style:** surface fill, 1px rule, 8px corners, 44px tall. Text is 1rem on mobile (prevents iOS zoom) and 0.875rem from 640px. The caret is accent-ink.
- **Focus:** the border and a 1px outline switch to accent-ink.
- **Error / Disabled:** `aria-invalid` turns the border and focus outline red. Disabled is 50% opacity. Form-level errors are an 8px-corner alert with red text on the subtle red tint.

### Navigation

- **Header:** wordmark "Pack" plus "Vote" in accent-ink, 600 weight. Nav items are slate text links, 44px tall, and turn foreground on hover. The current page's link is foreground with a 2px accent-ink underline at an 8px offset. Primary actions never live in the header.
- **Tabs:** an underline tab strip that scrolls horizontally without a scrollbar, over a 1px base rule. Tabs are 44px tall with slate labels (8px side padding, 12px from 640px). The active tab has foreground text, and a single 2px accent-ink indicator slides to it over 300ms with the long ease-out.

### Departures Board (signature)

The landing's board is a framed table on the surface color (4px corners, 1px rule). A caption line sits above a muted mono header band. Each destination name is a row of split-flap tiles. It is the one board that plays on load, once:

1. Round-one counts flip in.
2. The last option flips to a red ELIMINATED flap.
3. Its voters' chips slide to their next choice.
4. Round-two counts flip in.
5. The winning row fills yellow with inverted tiles and goes to BOARDING.

The flip is a 600ms `rotateX(-90deg → 0)` with `perspective(300px)`, staggered 45ms per letter. The chip move is a FLIP with `element.animate` (700ms, cubic-bezier(0.16, 1, 0.3, 1)). View Transitions are not used because they block hit-testing page-wide. Content that has not been revealed yet is faded, never removed, so assistive tech always gets the final state. Under reduced motion the board renders the final state and the Replay button is hidden.

### Motion

Every movement on the app screens answers a state change. Nothing plays on page load, except the generating indicator, which pulses while generation runs.

- **Flap tiles:** flip (600ms, 45ms stagger) only when a character changes after mount.
- **Gate strip:** the current status flap flips when the trip's status changes.
- **Results runoff:** 650ms per phase, only when the rounds change, on Replay, or on mount after a tab switch.
- **Ballot:** rows slide to their new rank in a 300ms FLIP.
- **Tabs:** the indicator slides over 300ms.
- **Yellow row:** row fill and tile colors cross-fade over 300ms.

Flips, FLIPs and the tab indicator use the ease-out `cubic-bezier(0.16, 1, 0.3, 1)`. Under reduced motion everything shows its final state. The global CSS rule collapses CSS animations and transitions, but it does not reach `element.animate`, so every WAAPI animation checks `prefers-reduced-motion` itself and is skipped, and the runoff never starts.

### Named Rules

**The State-Change Motion Rule.** On the app screens, motion means something changed. A screen that animates when it first appears is wrong.

## Do's and Don'ts

### Do:

- **Do** route every color through the `--color-*` tokens so both themes come from one class list.
- **Do** use `accent-ink` for any yellow-meaning text, ring, underline or icon, and `accent` only as a fill.
- **Do** keep exactly one yellow primary per screen.
- **Do** set codes, counts, initials and statuses in Geist Mono with tabular numerals.
- **Do** make status labels solid fills with their own text color.
- **Do** take trip status words and tones from the one `STATUS` table.
- **Do** keep every interactive target at least 44px tall.
- **Do** keep motion mechanical and short (180–700ms, ease-out `cubic-bezier(0.16, 1, 0.3, 1)`), and make reduced motion show the final state.
- **Do** check `prefers-reduced-motion` in code before any `element.animate` call.

### Don't:

- **Don't** put yellow text or a yellow stroke on a light surface.
- **Don't** put green or red text on the yellow fill.
- **Don't** fill a results row yellow before the trip is finalized.
- **Don't** use pill badges or tinted status tags; status is a solid flap.
- **Don't** add photography, illustrations or raster images.
- **Don't** add resting shadows to cards or panels.
- **Don't** use View Transitions for in-page movement; use FLIP with `element.animate`.
- **Don't** introduce a second accent hue or let warning orange drift toward the yellow.
