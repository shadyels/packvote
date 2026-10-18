import { Link } from "react-router-dom";
import { Ballot } from "@/components/Ballot";
import { TripRow } from "@/components/TripRow";
import { useAuth } from "@/hooks/useAuth";
import { buttonClass } from "@/components/ui/Button";
import type { DayItinerary, Itinerary, TripSummary } from "@/types";

const SAMPLE_TRIP: TripSummary = {
  id: 1,
  trip_code: "LISB2026",
  title: "Summer with the crew",
  destination: null,
  status: "VOTING",
  participant_count: 6,
  preferences_submitted_count: 6,
  created_at: "2026-05-02T10:00:00Z",
};

// Only the length is shown (the card is decorative), so stub days carry no activities.
const stubDays = (n: number): DayItinerary[] =>
  Array.from({ length: n }, (_, i) => ({
    day_number: i + 1,
    title: `Day ${(i + 1).toString()}`,
    activities: [],
    estimated_cost: null,
  }));

const option = (
  id: number,
  title: string,
  destination: string,
  budget: number,
  days: number
): Itinerary => ({
  id,
  trip_id: 1,
  iteration_number: 1,
  option_title: title,
  destination_name: destination,
  destination_description: "",
  daily_itinerary: stubDays(days),
  total_estimated_budget: budget,
  currency: "USD",
  match_reasoning: "",
  highlights: [],
  model_used: null,
  provider: null,
  created_at: "2026-05-03T10:00:00Z",
  estimated_cost: null,
  price_last_updated: null,
  price_source: null,
});

const SAMPLE_OPTIONS: Itinerary[] = [
  option(1, "Coastal food trail", "Lisbon, Portugal", 1450, 5),
  option(2, "Alpine hut hopping", "Dolomites, Italy", 1280, 4),
  option(3, "Island slow week", "Naxos, Greece", 1620, 6),
];

const STEPS = [
  ["Create and invite", "Set a travel window and email the group. Guests need no account."],
  ["Share preferences", "Everyone adds budget, dates and interests in a minute."],
  ["Get options", "AI reads the whole group and drafts day-by-day itineraries."],
  ["Rank and vote", "Each person ranks the options from best to worst."],
  ["Finalize", "The organizer locks in the winner and everyone is notified."],
] as const;

const primaryLink = buttonClass("primary");
const secondaryLink = buttonClass("secondary");

// React 18 typings have no `inert`; the string form lands in the DOM as a boolean attribute.
const inertProps = { inert: "" };

function Ctas() {
  const { isAuthenticated } = useAuth();
  return (
    <div className="flex flex-wrap gap-3">
      {isAuthenticated ? (
        <Link to="/dashboard" className={primaryLink}>
          Go to dashboard
        </Link>
      ) : (
        <>
          <Link to="/login" className={primaryLink}>
            Plan a trip
          </Link>
          <Link to="/join" className={secondaryLink}>
            Join with a code
          </Link>
        </>
      )}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="mx-auto flex w-full flex-col gap-20 py-4 sm:py-12">
      <section
        className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2"
        aria-labelledby="hero"
      >
        <div className="flex min-w-0 animate-slide-up flex-col items-start gap-6">
          <h1 id="hero" className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Group trips, decided fairly.
          </h1>
          <p className="max-w-md text-lg text-muted-foreground">
            Collect everyone&apos;s preferences, let AI draft the options, and settle it with a
            ranked vote. No group chat required.
          </p>
          <Ctas />
        </div>
        <div
          aria-hidden="true"
          {...inertProps}
          data-testid="hero-frame"
          className="pointer-events-none flex min-w-0 animate-fade-in flex-col gap-4 rounded-2xl border border-border bg-muted p-3 select-none sm:p-4"
        >
          <div className="overflow-hidden rounded-xl border border-border bg-surface">
            <TripRow trip={SAMPLE_TRIP} to="/dashboard" />
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <Ballot
              options={SAMPLE_OPTIONS}
              onSubmit={() => Promise.resolve()}
              submitLabel="Submit ranking"
            />
          </div>
        </div>
      </section>

      <section aria-labelledby="how">
        <h2 id="how" className="text-2xl font-semibold tracking-tight">
          How it works
        </h2>
        <ol className="mt-6 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-5">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="bg-surface p-4">
              <span className="font-mono text-xs text-muted-foreground tabular-nums">
                {(i + 1).toString().padStart(2, "0")}
              </span>
              <h3 className="mt-2 text-sm font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="fair" className="max-w-2xl">
        <h2 id="fair" className="text-2xl font-semibold tracking-tight">
          Why it&apos;s fair
        </h2>
        <p className="mt-3 text-muted-foreground">
          Votes use instant-runoff. If no option has a majority, the least popular is dropped and
          its voters&apos; next choices count instead, until one option wins. Nobody has to game
          their vote.
        </p>
      </section>

      <section
        aria-labelledby="cta"
        className="flex flex-col items-start gap-5 rounded-2xl border border-border bg-surface p-6 sm:p-10"
      >
        <h2 id="cta" className="text-2xl font-semibold tracking-tight">
          Ready to plan?
        </h2>
        <Ctas />
      </section>
    </div>
  );
}
