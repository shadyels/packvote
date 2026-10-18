# Frontend Architecture — PackVote

## Structure

```
frontend/src/
├── main.tsx              # Mounts BrowserRouter > AuthProvider > App; imports styles.css
├── App.tsx               # All routes; AppShell is the layout route for every page
├── styles.css            # Tailwind v4 entry: @theme tokens, dark overrides, base styles
├── types/index.ts        # API response types
├── lib/api.ts            # The only fetch layer (request(), per-resource objects, onUnauthorized)
├── lib/trip.ts           # STATUS, limits, maxTripDays, date helpers, cn()
├── contexts/AuthContext.tsx
├── hooks/useAuth.ts      # Re-exports useAuth from the context
├── hooks/useFetch.ts     # The one data-fetching hook (with polling)
├── components/           # Feature components (AppShell, Ballot, TripForm, OptionCard, ...)
│   └── ui/               # Primitives (Button, Dialog, Tabs, Select, Input, Field, Toaster, ...)
└── pages/                # Route components (Landing, Login, Dashboard, TripDetail, Trip, Join, ...)
```

Tests live next to the code in `__tests__/` folders (see Testing below).

## Stack

- **React 18 + Vite**, TypeScript strict. Functional components only.
- **Tailwind CSS v4** through `@tailwindcss/vite` (`frontend/vite.config.ts`). There is no `tailwind.config` and no PostCSS step; design tokens are CSS-first `@theme` variables in `styles.css`.
- **Primitives:** native controls first (`<input type="date">`, `<select>`, `<textarea>`). `@base-ui/react` is used only for **Dialog** (`components/ui/Dialog.tsx`) and **Tabs** (`components/ui/Tabs.tsx`). There is no Radix and no shadcn/ui.
- **Drag and drop:** `@dnd-kit/core` + `@dnd-kit/sortable` in `components/Ballot.tsx`.
- **Toasts:** `sonner`, mounted once in `AppShell` via `components/ui/Toaster.tsx`. Call `toast.success(...)` / `toast.error(...)` from `"sonner"`.
- **Icons:** `lucide-react`.
- **Fonts:** Geist and Geist Mono, loaded from Google Fonts in `frontend/index.html`.

Removed in the rebuild: shadcn/ui, Radix, react-day-picker, date-fns, class-variance-authority, tw-animate-css, postcss/autoprefixer, and the DatePicker component.

## Design Tokens and Theming

Tokens are defined in `frontend/src/styles.css`. Components use the semantic names only (`bg-surface`, `text-muted-foreground`, `border-border`, `text-accent`, `bg-danger-subtle`), never raw hex values.

- Light values are in `@theme`. Dark values are overrides under `@media (prefers-color-scheme: dark)`.
- Theme follows the OS setting only. There is no in-app toggle.
- Accent is emerald: `--color-accent` is `#047857` in light and `#34D399` in dark. There is no orange in the design.
- Contrast of text on its background is documented as at least 4.5:1 in both themes.
- Focus ring: `:focus-visible` uses a 2px `--color-accent` outline.

**Buttons:** `components/ui/Button.tsx` exports `Button` (variants `primary | secondary | ghost | danger`; sizes `sm | md | icon`) and `buttonClass(variant, size)`. Use `buttonClass` for a `<Link>` that should look like a button. `sm` is 36px high and becomes 44px on coarse pointers (`pointer-coarse:h-11`). `md` is 44px. `loading` shows a spinner and disables the button.

## Data Layer

**`lib/api.ts`** is the only place that calls `fetch`. It exposes `auth`, `trips`, `participants`, `votes`, `itineraries`, and `admin` objects, one method per endpoint. `VITE_API_URL` is read at build time and defaults to `http://localhost:8000`.

**`useFetch(fetcher, deps, { poll })`** (`hooks/useFetch.ts`) is the single hook for server data. Behaviour:
- `isLoading` is true only until the first load settles (success or error). Later refetches and polls keep the last data on screen.
- A failed refresh keeps the data and sets `error`. A failed first load leaves `data` null, so the page shows a Retry state.
- When `deps` change, the hook drops the old data and shows the loading state again.
- `refetch()` invalidates in-flight responses, so a stale response cannot overwrite newer data.
- `poll(data)` returns the delay in ms until the next request, or `null` to stop. A failed poll retries after the last delay used.
- A scheduled poll skips its request while the tab is hidden and reschedules the same delay. The first load on mount is not gated.

**Polling cadence** (verified in the page files):

| Page | Condition | Delay |
|---|---|---|
| Organizer `TripDetail` (`pollDelay`) | `GENERATING` | 5s |
| | `CREATED`, `COLLECTING_PREFERENCES`, `VOTING` | 15s |
| | any other status | none |
| Participant `Trip` | `GENERATING` | 5s |
| | any other status | none |

**Organizer load is all-or-nothing.** `TripDetail` loads trip, participants and options with `Promise.all`, then results if the status is `VOTING` or `FINALIZED`. If the first load fails, the page shows a full-page Retry. If a later poll fails, the page keeps the data and shows an inline "Couldn't refresh" note.

## Status and Limits

`STATUS` in `lib/trip.ts` maps each `TripStatus` to a label and a tone. The statuses are `CREATED`, `COLLECTING_PREFERENCES`, `GENERATING`, `GENERATION_FAILED`, `VOTING`, and `FINALIZED`. There is no `ITERATING` status.

Length limits (`TITLE_MAX`, `DESTINATION_MAX`, `NOTES_MAX`, `NAME_MAX`, `INTERESTS_MAX`, `ACTIVITY_TAG_MAX`, `ACTIVITY_TAGS_MAX_ITEMS`, `PARTICIPANT_EMAILS_MAX`, `PASSWORD_MIN`, `PASSWORD_MAX`) and `maxTripDays(numOptions)` mirror the backend in `backend/app/schemas/_limits.py`. Keep them in sync when the backend changes.

**Dates:** `parseDate` reads only the first 10 characters of an ISO string and builds a local-time `Date`, so `"2025-06-01"` and `"2025-06-01T00:00:00"` both show June 1 in every timezone. Use `formatDate`, `formatDateRange`, and `formatTimestamp` for display.

## Auth

**Token storage:** the JWT is stored in `localStorage` under `access_token`.

**`AuthContext`** (`contexts/AuthContext.tsx`) holds `user`, `isLoading`, `isAuthenticated`, `login`, `register`, and `logout`. `AuthProvider` wraps the app in `main.tsx`. Read it through `useAuth()`. Do not create a second auth state; that caused duplicate `auth.me()` calls.

- On boot, a token is validated with `GET /auth/me`. Only a 401 removes the token. Network and 5xx errors keep it so a reload can recover.

**Global 401 logout:** `request()` in `lib/api.ts` calls the `onUnauthorized` listeners on a 401 only when all of these hold:
- the call was made with a token,
- the stored token is still the same token (so a login in flight is not logged out),
- the path is not under `/auth/`, or it is `/auth/me`.

`AuthContext` subscribes and logs out. Login, register, and reset 401s are shown as bad-credential messages instead.

**Error messages:** a 422 `detail` array is flattened into one readable string, with each item's `msg` joined by `; `.

**Referrer:** `index.html` sets `<meta name="referrer" content="strict-origin-when-cross-origin">`.

**Participant access:** participants have no JWT. The participant pages use the token from the URL (`/trip/:token`). The frontend never sends `X-Participant-Token`. Participant results come from the trip-view payload.

## Routing

Defined in `App.tsx`. Every route is a child of `AppShell`.

| Path | Component | Notes |
|---|---|---|
| `/` | `Landing` | Public. Auth-aware header and CTA. |
| `/login` | `Login` | |
| `/reset-password` | `ResetPassword` | Reads `?token=` from the Brevo email link. |
| `/join` | `Join` | Trip code + PIN form. |
| `/join/:token` | `JoinRedirect` | Invitation email link. Redirects to `/trip/:token`. |
| `/trip/:token` | `Trip` | Participant page. |
| `/trip/:token/vote` | `Trip` | Voting email link. Same page; focuses the ballot when the trip is `VOTING`. |
| `/dashboard` | `Dashboard` | Requires login (`ProtectedRoute`). |
| `/dashboard/trip/:tripId` | `TripDetail` | Organizer page. Requires login. |
| `*` | `NotFound` | |

**Protected routes:** `ProtectedRoute` shows skeletons while auth is loading, then redirects to `/login` if the user is not authenticated.

**Tabs use the URL.** The active tab is read from `?tab=` and changed with `setSearchParams(..., { replace: true })`. Do not keep the active tab in `useState`.
- `Dashboard`: `?tab=created` (default) or `?tab=invited`. An unknown value falls back to `created`.
- `TripDetail`: `?tab=overview` (default), `participants`, `options`, or `results`. An unknown value falls back to `overview`.

**Back navigation:** invited trips on the dashboard link to `/trip/:token` with `location.state = { from: "dashboard-invited" }`. `Trip` shows a "My trips" link back to `/dashboard?tab=invited` only when that state is present. Email-link visitors do not see it. The state is only for UI context; anything that must survive a reload belongs in the URL.

**Standalone pages:** `Landing` and the auth pages render inside `AppShell`, which provides the header, footer, skip link, and toaster. `AppShell` shows auth-aware nav: "Dashboard" and "Log out" when signed in, "Join a trip" and "Sign in" otherwise.

## Components

Feature components in `components/`:

- **`Ballot`**: the ranked-choice input. A `dnd-kit` sortable list plus Up and Down buttons on every row. It is used by the participant page, the organizer's own vote, and the landing hero.
  - Sensors: pointer (5px activation distance), touch (150ms delay), keyboard.
  - Screen-reader announcements name the option title and its position, instead of dnd-kit's default raw IDs.
  - It takes `options`, `onSubmit(ids)`, and `submitLabel`. It resets its order when the option set changes.
- **`OptionCard`**: one itinerary. The heading is `optionTitle(o)` = `option_title ?? destination_name`. Pass `winner` and `dimmed` for the results view.
- **`Results`**: the round-by-round vote breakdown.
- **`TripForm`**: create and edit forms (`trip` prop = edit mode). Used in dialogs.
- **`PreferenceForm`**: participant preference form. Pre-fills dates from the organizer's proposal.
- **`GeneratingState`**: the generating and failed states.
- **`TripRow`**: one trip in a dashboard list. Also used by the landing hero.
- **`EmptyState`**, **`AppShell`**, **`ProtectedRoute`**.

Primitives in `components/ui/`:

- **`Dialog`**: controlled modal on `@base-ui/react/dialog`. Bottom sheet below `sm`, centered card from `sm` up. Enter and exit are CSS transitions driven by base-ui's `data-starting-style` and `data-ending-style`.
- **`Tabs`**: `Tabs`, `TabsList`, `TabsTab`, `TabsPanel` on `@base-ui/react/tabs`. The list scrolls horizontally on narrow screens. Tabs are 44px high.
- **`Button`**, **`Input`**, **`Select`**, **`Textarea`**, **`Field`**, **`Badge`**, **`Skeleton`**, **`Spinner`**, **`Toaster`**.

**Landing hero:** `Landing` renders a real `TripRow` and `Ballot` with sample data inside a frame marked `inert` and `aria-hidden="true"`. The `inert` attribute is passed as a string prop because React 18 typings do not include it.

**Async handlers:** ESLint enforces `@typescript-eslint/no-misused-promises`. Wrap async handlers:

```tsx
onClick={() => { void handleAsync(); }}
onSubmit={(e) => { void handleSubmit(e); }}
```

## Accessibility and Motion

- **Skip link:** `AppShell` renders "Skip to content", which targets `<main id="main">`.
- **Touch targets:** interactive controls are at least 44px on coarse pointers.
- **Live regions:** status and error messages use `role="status"` or `role="alert"`. `Ballot` announces moves through a polite live region.
- **Icons** are `aria-hidden="true"`. Icon-only buttons have an `aria-label` (for example, "Close" in `Dialog` and "Copy trip code ...").
- **Reduced motion:** `styles.css` shortens all animations and transitions to 0.01ms under `prefers-reduced-motion: reduce`.
- **Animations:** `fade-in` (page entry) and `slide-up` (`--animate-slide-up`) are the only custom keyframes, both defined as `@theme` animation tokens in `styles.css`.

## Testing

Vitest with jsdom, React Testing Library, and `globals: true`. Config is in `frontend/vitest.config.ts`. The setup file is `frontend/tests/setup.ts`.

Test files (`__tests__/` folders):

- `src/__tests__/routes.test.tsx`
- `src/pages/__tests__/`: `Dashboard`, `Join`, `Landing`, `Login`, `Trip`, `TripDetail`
- `src/components/__tests__/`: `Ballot`, `OptionCard`, `PreferenceForm`, `ProtectedRoute`, `Results`, `TripForm`
- `src/hooks/__tests__/useFetch.test.ts`
- `src/lib/__tests__/`: `api.test.ts`, `trip.test.ts`
- `src/contexts/__tests__/AuthContext.test.tsx`

Run from `frontend/`: `pnpm test --run` (one run). Bare `pnpm test` starts Vitest in watch mode.
