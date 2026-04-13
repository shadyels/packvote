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
- `GET /trips/{trip_id}/participants` — creator-only, includes email. Each row includes `has_voted_current_iteration: bool` (whether the participant has voted in the current iteration) and `preferences_submitted: bool`. The creator appears as a regular participant row (identifiable by their email matching the authenticated user's email); no separate `is_admin` flag is returned.
- `GET /trips/{trip_id}/itineraries` — creator-only, all iterations
- `GET /trips/{trip_id}/ai-logs` — creator-only AI call log history

**`ParticipantsSection` — adaptive column keyed on trip status:**
`frontend/src/components/dashboard/ParticipantsSection.tsx` accepts `participants: Participant[]` and `trip: Trip`. During `VOTING` / `ITERATING` the column header and counter switch from "Preferences" to "Voted" and use `has_voted_current_iteration` instead of `preferences_submitted` for the progress bar and per-row icon. All other statuses keep the preferences column. The authenticated user's row gets an **Organizer** badge — identified by matching `p.email === auth.user?.email` via `useAuth()` (the creator-only endpoint guarantees the dashboard viewer is the trip creator).

**`TripOverviewSection` — admin vote gate:**
`frontend/src/components/dashboard/TripOverviewSection.tsx` accepts `participants: Participant[]`. It locates the creator's row by `p.email === user.email` and reads `has_voted_current_iteration`. During `VOTING`, if the creator has not yet voted the drag-to-rank form is shown; once voted, a green "Your vote is in · Waiting on N more participants" confirmation card replaces it. When `nonVoterCount === 0` (everyone voted, auto-tally imminent) the message reads "All participants have voted — results coming up."

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
`frontend/src/components/trip/` — `TripHeader`, `TripDetails`, `ParticipantProgress`, `PreferenceForm`, `WaitingScreen`, `GeneratingScreen`, `VotingForm`, `WinnerDisplay`, `SortableRankItem`. `TripPage.tsx` is the state machine rendering the correct one based on status and `has_voted`.

**`TripDetails` component:**
Shown between `TripHeader` and `PreferenceForm` during `CREATED`/`COLLECTING_PREFERENCES` status. Displays the organizer's proposed destination, date range, and notes in a prominent card with brand-coloured icons. Hidden if the trip has no details to show. `notes` is included in `TripPublicInfo` (backend schema + frontend type) so participants can see the admin's notes.

**`PreferenceForm` pre-fills from organizer proposal:**
Accepts a `trip: TripPublicInfo` prop. Date pickers are initialised with the admin's `proposed_start_date`/`proposed_end_date` (parsed via `date-fns/parseISO`) so participants can accept the suggested dates or override them. A hint line ("Organizer suggested … — change if needed") is shown above the date grid when proposed dates exist.

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
  - `isWinner` — applies green border + glow + Winner badge
  - `isGreyedOut` — applies `opacity-50 grayscale` to visually dim non-winner cards; pass `winnerId !== null && it.id !== winnerId` in any list that has a winner
  - In both `ItinerariesSection` (admin) and `VotingForm` (participant), itineraries are sorted winner-first when `winnerId` is set
  - **`option_title` as primary heading:** `CardTitle` displays `option_title ?? destination_name`. `destination_name` is always rendered as a subtitle below it (used for Unsplash image lookup). Never swap these — `destination_name` must stay as the image key.
  - **Activity display — hybrid overview + drawer:** Daily itinerary renders as an always-visible list of compact day rows (title + activity count + activity pill tags). `VISIBLE_DAY_LIMIT = 5` (module-level constant) — trips longer than 5 days show a "Show N more days ↓ / Show fewer days ↑" toggle. Clicking a row opens `DayDetailDrawer`. The old expand/collapse flat list is removed.

- `DayDetailDrawer` — `frontend/src/components/shared/DayDetailDrawer.tsx`
  - Props: `{ days: DayItinerary[], initialDayIndex: number, open: boolean, onOpenChange, currency? }`
  - **Mobile:** fixed bottom-sheet (`bottom-0 rounded-t-xl max-h-[85vh]`) with drag handle. Enters with `animate-slide-up`. Exit animation (`animate-slide-down`) is set via `data-closed:` but does not play to completion — `@base-ui/react` removes the DOM node immediately on close (known limitation; enter animation works correctly).
  - **Desktop (sm+):** centered modal (`max-w-md rounded-xl`) with fade+zoom via `data-open:animate-in data-open:zoom-in-95`.
  - Uses `DialogPrimitive.Popup` from `@base-ui/react/dialog` directly (not the project's wrapped `DialogContent`) — required for bottom-sheet positioning.
  - `currentDayIndex` syncs to `initialDayIndex` on open. ArrowLeft/ArrowRight keyboard shortcuts navigate between days.
  - Renders `DailyActivity.estimated_cost` (if not null) as `~{currency}{cost} per person` in brand orange.

- `STATUS_CONFIG` — `frontend/src/lib/trip-status.ts`
- `parseJson` (safe JSON.parse with fallback) — `frontend/src/lib/utils.ts`

## CSS Animations

`globals.css` defines `@keyframes`: `fade-in-up`, `fade-in`, `shimmer`, `progress`, `slide-up`, `slide-down`. The `GeneratingScreen` indeterminate progress bar uses `animate-[progress_40s_linear_infinite]`. `animate-slide-up` (0.3s ease-out) and `animate-slide-down` (0.25s ease-in) are used by `DayDetailDrawer` for mobile bottom-sheet entrance/exit.

## Landing Page

Standalone layout outside `LayoutWrapper` — own nav header and `<Footer />`. Route declared at top level before `LayoutWrapper`.

Hero uses radial vignette overlay. Bottom CTA section: `bg-[#192840]` with top fade dissolving from offwhite. Feature Highlights section uses `rounded-3xl bg-card border border-border` floating card container.
