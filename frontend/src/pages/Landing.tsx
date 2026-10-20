import { Link } from "react-router-dom";
import { ArrowDown, ArrowRight } from "lucide-react";
import { BOARD_FACTS, DeparturesBoard } from "@/components/DeparturesBoard";
import { useAuth } from "@/hooks/useAuth";
import { buttonClass } from "@/components/ui/Button";

const STEPS = [
  [
    "Invite",
    "The organizer creates a trip and emails the group. Friends join from the link, or with a trip code and PIN. No account needed.",
  ],
  [
    "Everyone ranks",
    "Everyone shares their preferences, AI drafts itinerary options from the whole group, and each person ranks them.",
  ],
  [
    "Fair winner",
    "Instant-runoff picks the winner, the trip is finalized and everyone is emailed.",
  ],
] as const;

const FAQ = [
  [
    "What happens on a tie?",
    "If every remaining option has the same number of votes there is no winner, and the trip stays open for voting. The organizer then picks the winner or, if rounds remain, asks for new options. A tie for last place is broken by a fixed rule, so the same votes always give the same result.",
  ],
  [
    "What if someone doesn't vote?",
    "The winner is locked in automatically once everyone has voted. Until then the organizer can pick the winner or ask for new options. Votes not cast are not counted.",
  ],
  [
    "Do my friends need an account?",
    "No. Friends vote from their invitation link, or with the trip code and PIN from the invitation. Only the organizer needs one.",
  ],
] as const;

const primaryLink = buttonClass("primary");
const secondaryLink = buttonClass("secondary");

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
  const { total, needed, leader, winner, out, names, r1, r2 } = BOARD_FACTS;
  return (
    <div className="flex w-full flex-col py-2 sm:py-8">
      <section aria-labelledby="landing-hero" className="flex flex-col items-start gap-5">
        <h1
          id="landing-hero"
          className="w-full text-[clamp(3rem,7vw,6rem)] leading-[0.98] font-semibold tracking-tight text-balance"
        >
          Group trips, decided fairly.
        </h1>
        <p className="max-w-3xl text-lg text-pretty text-muted-foreground">
          Collect everyone&apos;s preferences, let AI draft the options, settle it with a ranked
          vote.
        </p>
        <Ctas />
      </section>

      <div className="mt-8 sm:mt-12">
        <DeparturesBoard />
      </div>

      <section aria-labelledby="landing-how" className="mt-20 sm:mt-28">
        <h2 id="landing-how" className="text-2xl font-semibold tracking-tight">
          How it works
        </h2>
        <ol className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="flex flex-1 flex-col gap-3 sm:flex-row">
              <div className="flex-1 border-t-2 border-foreground pt-3">
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{body}</p>
              </div>
              {i < STEPS.length - 1 && (
                <>
                  <ArrowRight
                    className="mt-3 hidden size-6 shrink-0 text-accent-ink sm:block"
                    aria-hidden="true"
                  />
                  <ArrowDown className="size-6 text-accent-ink sm:hidden" aria-hidden="true" />
                </>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section
        aria-labelledby="landing-fair"
        className="mt-16 rounded-2xl bg-accent p-6 text-accent-foreground sm:mt-24 sm:p-10 [&_:focus-visible]:outline-accent-foreground"
      >
        <h2
          id="landing-fair"
          className="max-w-3xl text-3xl font-semibold tracking-tight text-balance sm:text-5xl"
        >
          {names[leader]} led round one and still lost.
        </h2>
        <p className="mt-4 max-w-2xl text-lg">
          Nobody reached {needed.toString()} of {total.toString()} votes, so {names[out]}, last with{" "}
          {r1[out].toString()}, was dropped and its voters&apos; next choice counted instead.{" "}
          {names[winner]} finished {r2[winner].toString()} to {r2[leader].toString()}. That is
          instant-runoff: nobody has to game their vote.
        </p>
        <div className="mt-8 max-w-2xl divide-y divide-accent-foreground/30 border-y border-accent-foreground/30">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-3">
              <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-4 font-medium [&::-webkit-details-marker]:hidden">
                {q}
                <ArrowDown
                  className="size-5 shrink-0 transition-transform group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <p className="pb-2">{a}</p>
            </details>
          ))}
        </div>
      </section>

      <section aria-labelledby="landing-go" className="mt-16 flex flex-col gap-5 sm:mt-24">
        <h2 id="landing-go" className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Your friends don&apos;t need an account.
        </h2>
        <Ctas />
      </section>
    </div>
  );
}
