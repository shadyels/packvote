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
  boarding-green-subtle: "#e3f4ea"
  eliminated-red: "#b42318"
  eliminated-red-subtle: "#fdecea"
  warning-orange: "#b4370a"
  warning-orange-subtle: "#ffedd5"
  flap-ink: "#f4f5f7"
  board-night: "#0b0f17"
  board-panel: "#141a24"
  board-muted: "#1c2330"
  board-white: "#edeff2"
  board-slate-text: "#9aa3b2"
  board-rule: "#2a3343"
  board-yellow-subtle: "#2b2410"
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
  badge:
    backgroundColor: "{colors.concrete-muted}"
    textColor: "{colors.slate-text}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
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
  status-flap-boarding:
    backgroundColor: "{colors.boarding-green}"
    textColor: "{colors.concrete}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  status-flap-eliminated:
    backgroundColor: "{colors.eliminated-red}"
    textColor: "{colors.concrete}"
    typography: "{typography.label}"
    rounded: "{rounded.flap}"
    padding: "0 8px"
    height: "28px"
  tab-active:
    textColor: "{colors.sign-black}"
    height: "44px"
    padding: "0 12px"
---

# Design System: PackVote

## Overview

**Creative North Star: "The Departures Hall"**

PackVote borrows the two faces of an airport. Dark mode is the departures board: a blue-black ground, near-black split-flap cells, cool-white type and one signal yellow. Light mode is the wayfinding sign: cool concrete grey, solid yellow panels, black type. Both themes follow `prefers-color-scheme`, and there is no toggle. Both read as public, legible information rather than decoration. The group's vote is shown as a board resolving, with flaps turning and a row going to BOARDING, not as a chart.

Density is calm. A single centred column (64rem) holds generous section gaps. Type is large and tight-tracked for statements, and monospaced for data: codes, counts, statuses. Depth comes from tone and hairline rules, not shadows. Motion is mechanical and short: tiles flip down into place, and chips slide to their new row with a long ease-out.

The product rule "no photography or imagery anywhere" holds visually too: there are no rasters, illustrations or hero images. The board, type and yellow carry the identity.

**Key Characteristics:**
- Two themes, one world: departures board (dark) and wayfinding sign (light).
- Signal yellow is the only accent, used sparingly and on purpose.
- Geist for statements, Geist Mono for anything a board would print.
- Flat, rule-separated surfaces. Shadows only on lifted interaction states.
- Status colors are solid fills, read the way an airport reads them: green = boarding/winner, red = eliminated.

## Colors

The palette is cool, blue-grey neutrals with one hot signal yellow and two status colors. Frontmatter keys prefixed `board-` are the dark-theme values of the same semantic roles. The app consumes them through `--color-*` custom properties in `src/styles.css`, so components never pick a theme by hand.

### Primary
- **Signal Yellow** (`signal-yellow`, both themes): the only accent. It fills the primary button, the "fair winner" panel, the BOARDING row on the board, and text selection. Text on it is always the foreground near-black (`--color-accent-foreground`).

### Secondary
- **Boarding Green** (`boarding-green` light / `board-green` dark): success, the winner and BOARDING. Solid fill for status flaps, text color on its subtle tint for badges.
- **Eliminated Red** (`eliminated-red` light / `board-red` dark): danger, elimination and destructive actions. Same fill/tint pattern.

### Tertiary
- **Warning Orange** (`warning-orange` light / `board-orange` dark): warnings only. It is deliberately burnt so it never reads as the yellow accent.

### Neutral
- **Concrete** (`concrete`) / **Board Night** (`board-night`): page background.
- **Sign White** (`sign-white`) / **Board Panel** (`board-panel`): surfaces: cards, the board, inputs, the secondary button.
- **Concrete Muted** (`concrete-muted`) / **Board Muted** (`board-muted`): table header band, voter chips, neutral badges, hover fills.
- **Sign Black** (`sign-black`) / **Board White** (`board-white`): foreground text.
- **Slate Text** (`slate-text`) / **Board Slate Text** (`board-slate-text`): secondary text, captions, inactive tabs and nav.
- **Concrete Rule** (`concrete-rule`) / **Board Rule** (`board-rule`): every border and divider (it is the global default border color).
- **Flap** (`sign-black` light / `board-flap` dark) with **Flap Ink** (`flap-ink` / `board-white`): split-flap letter tiles. They are near-black in both themes and carry a faint white inset edge (`#ffffff1a`) in dark only.

### Named Rules
**The Fill-Only Yellow Rule.** In light mode yellow is only ever a fill. Text, focus rings, caret, active-tab underlines and accent arrows use `--color-accent-ink`, which is sign black in light and signal yellow in dark. `--color-accent-subtle` is the solid yellow in light and a dark olive (`board-yellow-subtle`) in dark. Never put yellow text or a yellow stroke on a light surface.

**The One Yellow Primary Rule.** Exactly one yellow primary action per screen. Secondary navigation that duplicates it (for example the header "Sign in") is a text link, not a button.

**The Solid Status Rule.** Status labels on the board are solid fills with their own text color (green BOARDING, red ELIMINATED, muted RUNNER-UP), so they stay legible on the yellow winner row in both themes. Green or red text on yellow fails in dark and is not allowed.

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
- **Flap** (Geist Mono 500, uppercase, 0.875rem → 1rem at 768px → 1.25rem at 1024px): one letter per split-flap tile.

### Named Rules
**The Board Prints Mono Rule.** Anything a board would print (destination codes, initials, vote counts, statuses, trip codes and PINs) is Geist Mono with tabular numerals. Prose, headings and buttons are never mono.

## Layout

The page is a single centred column, `max-width: 64rem`, with 16px side padding and a sticky 56px header (background at 90% opacity with backdrop blur). Sections stack vertically with large, stepped gaps: 64–80px on mobile, 96–112px from 640px. Inside sections, the rhythm runs on 4/8/12/20/24px gaps.

The board is the hero object at full content width, never a side card. It responds in three steps. Below 768px each row is a stacked grid (name across the top, voters and counts on the second line, status on the third) and the column headers are visually hidden. From 768px (`md`) it is a real table. From 1024px (`lg`) the tiles grow to 32×44px and the R1/R2/Status columns take fixed widths (7rem, 7rem, 11rem).

Step sequences run horizontally from 640px, with accent-ink arrows between steps, and vertically below it with down arrows. Every interactive target is at least 44px tall. Small buttons grow to 44px on coarse pointers.

## Elevation & Depth

The system is flat. Surfaces separate by tone (concrete → white, or night → panel) and by 1px rules in the border color. Section breaks use a 2px foreground top rule over step columns. The only shadows are interaction states: a dragged ballot row lifts, and the mobile bottom-sheet dialog sits over a scrim (`--color-overlay`).

### Shadow Vocabulary
- **Lifted drag** (Tailwind `shadow-lg` plus a 1px accent-ink ring): a ballot row while it is being dragged.
- **Sheet** (Tailwind `shadow-xl`): the dialog popup over the overlay.

### Named Rules
**The Flat-At-Rest Rule.** Nothing casts a shadow at rest. Depth appears only when the user picks something up or opens something over the page.

## Shapes

Corners scale with the size of the object. Split-flap tiles, status flaps, voter chips and the board frame use 4px corners, which reads mechanical. Buttons and inputs use 8px. Cards, empty states and ballot rows use 12px. Badges are pills. The yellow feature panel uses 16px, as does the top edge of the bottom-sheet dialog. Each flap tile is split by a 1px horizontal midline (black at 60%), the one decorative geometry in the system and the mark of a split-flap cell.

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
- **Badges:** pill, 0.75rem medium. Tones put the semantic text color on its subtle tint (neutral, accent, success, warning, danger).

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** surface on the page background.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px rule. The winning option adds a 1px accent-ink border plus ring. Dimmed options drop to 60% opacity.
- **Internal Padding:** 16px (empty and generating states 20–24px horizontal, 48px vertical).

### Inputs / Fields
- **Style:** surface fill, 1px rule, 8px corners, 44px tall. Text is 1rem on mobile (prevents iOS zoom) and 0.875rem from 640px. The caret is accent-ink.
- **Focus:** the border and a 1px outline switch to accent-ink.
- **Error / Disabled:** `aria-invalid` turns the border and focus outline red. Disabled is 50% opacity.

### Navigation
- **Header:** wordmark "Pack" plus "Vote" in accent-ink, 600 weight. Nav items are slate text links, 44px tall, and turn foreground on hover. Primary actions never live in the header.
- **Tabs:** an underline tab strip that scrolls horizontally without a scrollbar. Tabs are 44px tall with slate labels. The active tab gets a 2px accent-ink underline and foreground text.

### Departures Board (signature)
The board is a framed table on the surface color (4px corners, 1px rule). A caption line sits above a muted mono header band. Each destination name is a row of split-flap tiles. The sequence plays once on load:
1. Round-one counts flip in.
2. The last option flips to a red ELIMINATED flap.
3. Its voters' chips slide to their next choice.
4. Round-two counts flip in.
5. The winning row fills yellow with inverted tiles and goes to BOARDING.

The flip is a 600ms `rotateX(-90deg → 0)` with `perspective(300px)`, staggered 45ms per letter. The chip move is a FLIP with `element.animate` (700ms, cubic-bezier(0.16, 1, 0.3, 1)). View Transitions are not used because they block hit-testing page-wide. Content that has not been revealed yet is faded, never removed, so assistive tech always gets the final state. Under reduced motion the board renders the final state and the Replay button is hidden.

## Do's and Don'ts

### Do:
- **Do** route every color through the `--color-*` tokens so both themes come from one class list.
- **Do** use `accent-ink` for any yellow-meaning text, ring, underline or icon, and `accent` only as a fill.
- **Do** keep exactly one yellow primary per screen.
- **Do** set codes, counts, initials and statuses in Geist Mono with tabular numerals.
- **Do** make status labels solid fills with their own text color.
- **Do** keep every interactive target at least 44px tall.
- **Do** keep motion mechanical and short (180–700ms, ease-out `cubic-bezier(0.16, 1, 0.3, 1)`), and make reduced motion show the final state.

### Don't:
- **Don't** put yellow text or a yellow stroke on a light surface.
- **Don't** put green or red text on the yellow fill.
- **Don't** add photography, illustrations or raster images.
- **Don't** add resting shadows to cards or panels.
- **Don't** use View Transitions for in-page movement; use FLIP with `element.animate`.
- **Don't** introduce a second accent hue or let warning orange drift toward the yellow.
