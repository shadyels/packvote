# Itinerary Option Title — Design Spec

**Date:** 2026-04-13
**Branch:** `refactor/option-title`
**Status:** Approved

## Problem

Itinerary cards display `destination_name` (e.g. "Lisbon, Portugal") as the only heading. When multiple options are generated, all cards look like generic location labels — there is no way to distinguish them at a glance or give them personality.

## Goal

Add a creative, thematic `option_title` field to each itinerary option (e.g. "Coastal Culture Crawl", "Ramen, Rails & Rooftops"). The title captures the trip's personality and is distinct from the destination name. The destination name is demoted to a subtitle.

## Design

### Data model

Add a single nullable `option_title VARCHAR(255)` column to the `itineraries` table. Nullable so existing rows are not broken.

### AI prompt

Add `option_title` as the first field in each option's JSON schema inside `ITINERARY_PROMPT_V2`. Add a writing style rule:

> `option_title`: A creative 3-5 word thematic name capturing the trip's personality. Must NOT contain the destination name. Examples: "Coastal Culture Crawl", "Ramen, Rails & Rooftops", "Old Town Budget Blitz".

### Backend layers

- `ItineraryOption` (AI output schema): add `option_title: str`
- `ItineraryResponse` (API response schema): add `option_title: str | None`
- `Itinerary` SQLAlchemy model: add `option_title: Mapped[str | None]`
- `_do_generation`: map `option.option_title` to the DB constructor

### Frontend

- `Itinerary` TypeScript interface: add `option_title: string | null`
- `ItineraryCard`: `option_title` as `<CardTitle>`, `destination_name` as subtitle. Keep `destination_name` for Unsplash image lookup.
- `SortableRankItem`, `TripOverviewSection`, `VotingSection`: use `option_title ?? destination_name` pattern everywhere
- Fallback: if `option_title` is null (old data), display `destination_name` as the title

### Testing

Live test `TestPromptV2Compliance` gains an assertion: `option_title` is present, non-empty, and does not equal `destination_name`.

## Constraints

- No breaking changes to existing rows (nullable column, frontend fallback)
- `destination_name` remains the authoritative field for image lookup (Unsplash)
- `option_title` is AI-generated — no client-side generation
