# Frontend Architecture — PackVote

## shadcn/ui is @base-ui/react

The shadcn components in this project use `@base-ui/react` primitives (not `@radix-ui`). Key API differences:
- `DialogTrigger` has no `asChild` — use `render` prop: `<DialogTrigger render={<Button />} />`
- `Select.Root` `onValueChange` callback is `(value: string | null, eventDetails) => void` — guard against null before calling setState
- `Tabs` uses `data-[active]:` for active tab styling (Tailwind v3 arbitrary data-attribute variant — NOT `data-active:` which is invalid syntax and generates nothing)
- `TabsList` `line` variant includes `overflow-x-auto scrollbar-hide` for horizontal scroll on mobile. `.scrollbar-hide` is defined in `globals.css`.

**Async event handler lint rule:**
The project enforces `@typescript-eslint/no-misused-promises`. Wrap async handlers:
```tsx
onClick={() => { void handleAsync(); }}
onSubmit={(e) => { void handleSubmit(e); }}
```

## Auth & Routing

**AuthContext pattern:**
`frontend/src/contexts/AuthContext.tsx` provides shared auth state (user, isLoading, isAuthenticated, login, register, logout). `AuthProvider` wraps the app in `main.tsx`. `useAuth` in `hooks/useAuth.ts` re-exports from context. Never use standalone hook pattern — that caused multiple `auth.me()` calls.

**ProtectedRoute:**
`frontend/src/components/ProtectedRoute.tsx` guards authenticated routes. Shows skeletons while loading, redirects to `/login` if unauthenticated.

**Routing layout pattern:**
`LayoutWrapper` in `App.tsx` wraps non-login/non-landing routes with the nav via `<Outlet />`. `LoginPage` and `LandingPage` render their own full-screen layouts outside `LayoutWrapper`.

**Routes:**
- `/trip/:token/vote` → same `TripPage` (voting notification emails link here)
- `/join/:token` → `JoinRedirect` — redirects to `/trip/:token` (invitation email links)
- `/join` → `JoinPage` (trip code + PIN form, no email required)

## Dashboard (F8)

**`useTripDetail` hook:**
`frontend/src/hooks/useTripDetail.ts` orchestrates parallel fetches (trip, participants, itineraries, voting results, AI logs) via `Promise.allSettled`. Polls every 5s when `trip.status === "GENERATING"`, stops on status change or unmount.

**Dashboard sub-resource endpoints:**
- `GET /trips/{trip_id}/participants` — creator-only, includes email
- `GET /trips/{trip_id}/itineraries` — creator-only, all iterations
- `GET /trips/{trip_id}/ai-logs` — creator-only AI call log history

**Trip editing — `PATCH /trips/{trip_id}`:**
Editable fields: `title`, `destination`, `proposed_start_date`, `proposed_end_date`, `num_options`, `notes`. Only allowed when status is `CREATED`, `COLLECTING_PREFERENCES`, or `GENERATION_FAILED` — returns 409 otherwise. Frontend: `EditTripDialog` at `frontend/src/components/dashboard/EditTripDialog.tsx`.

**Trip deletion — cascade pattern:**
`DELETE /trips/{trip_id}` returns 204. Manual ordered bulk deletes (no DB-level CASCADE). Blocked with 409 when `trip.status == "GENERATING"`. Deletion order:
1. `vote_rounds` → `votes` → `preferences` → `ai_call_logs`
2. Set `trip.winner_itinerary_id = None` + `flush()` (breaks circular FK before deleting itineraries)
3. `itineraries` → `participants` → trip row

**Frontend 204 handling:**
`frontend/src/lib/api.ts` guards `res.json()` on empty body:
```ts
if (res.status === 204) return undefined as T;
```
Use `request<void>(...)` for any 204 endpoint.

## Participant Trip Page (F7)

**Composite endpoint `GET /participants/{token}/trip-view`:**
Returns `ParticipantTripView` with participant info, trip public info, participant briefs (names + submitted status, no emails), current-iteration itineraries, voting results, and `has_voted`. Token is the auth — no bearer token.

**`POST /participants/access-by-code`:**
Payload: `{ trip_code, pin }`. PIN is per-participant, so `trip_code + pin` uniquely identifies a participant. Returns `{ token, participant }`.

**`useTripView` hook:**
`frontend/src/hooks/useTripView.ts` polls every 5s while `trip.status === "GENERATING"`, stops on status change or unmount.

**Participant trip component structure:**
`frontend/src/components/trip/` — `TripHeader`, `ParticipantProgress`, `PreferenceForm`, `WaitingScreen`, `GeneratingScreen`, `VotingForm`, `WinnerDisplay`, `SortableRankItem`. `TripPage.tsx` is the state machine rendering the correct one based on status and `has_voted`.

**Drag-to-reorder voting (`VotingForm` + `SortableRankItem`):**
Uses `@dnd-kit/core` + `@dnd-kit/sortable`. State: `orderedIds: number[]`. Three sensors: `PointerSensor` (5px threshold), `TouchSensor` (150ms delay), `KeyboardSensor`. A `DragOverlay` renders a floating clone during drag.
`SortableRankItem` only gives `useSortable` listeners to the handle element — prevents mobile scroll hijack.
The same pattern is used in `TripOverviewSection` (admin dashboard) for the trip creator's vote during `VOTING` status.

## DatePicker Component

`frontend/src/components/ui/date-picker.tsx` — 3-level drill-down navigation (days → months → years). Key rules:
- Drill-down: click month/year caption → month grid; click year header → 12-year grid
- `startMonth` is always current month — no past month navigation in day view
- Selecting a day closes the popover via `setOpen(false)` in `onSelect`
- State in consumers is `Date | undefined`; formatted to `"yyyy-MM-dd"` via `date-fns/format` only at submit time
- Dependencies: `react-day-picker` v9, `date-fns` v4

**CRITICAL — Popover trigger uses a plain `<button>` element, NOT `<Button asChild>`:**
Radix's `asChild` clones `onClick`/`aria-*` onto the child; Base UI's `ButtonPrimitive` does not forward those cloned props to the DOM. The trigger is styled with `buttonVariants({ variant: "outline" })`. Do not revert to `<Button asChild>` or the popover will silently stop opening.

## Unsplash Image Utility

`frontend/src/lib/unsplash.ts` provides `useDestinationImage(destination, imageIndex = 0, totalCount = 1)` → `{ imageUrl, gradient, isLoading }`.
- `totalCount` → `per_page` in API call; `imageIndex` selects `results[imageIndex % results.length]`
- Consumers pass `imageIndex={index}` and `totalImages={items.length}` from `.map()` callbacks
- API key from `VITE_UNSPLASH_ACCESS_KEY`
- In-memory cache keyed by destination, 1-hour TTL; refetches if cached array is smaller than `totalCount`
- **Fallback:** deterministic gradient from destination name hash mixed with `imageIndex` when no API key or fetch fails
- No Unsplash attribution rendered anywhere
- Use index access, not `Array.prototype.at()` — unavailable under `lib: ["ES2020"]`

## Shared Components

- `ItineraryCard` — `frontend/src/components/shared/ItineraryCard.tsx`
- `STATUS_CONFIG` — `frontend/src/lib/trip-status.ts`
- `parseJson` (safe JSON.parse with fallback) — `frontend/src/lib/utils.ts`

## CSS Animations

`globals.css` defines `@keyframes`: `fade-in-up`, `fade-in`, `shimmer`, `progress`. The `GeneratingScreen` indeterminate progress bar uses `animate-[progress_40s_linear_infinite]`.

## Landing Page

Standalone layout outside `LayoutWrapper` — own nav header and `<Footer />`. Route declared at top level before `LayoutWrapper`.

Hero uses radial vignette overlay. Bottom CTA section: `bg-[#192840]` with top fade dissolving from offwhite. Feature Highlights section uses `rounded-3xl bg-card border border-border` floating card container.
