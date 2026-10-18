import { useEffect, useRef } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check } from "lucide-react";
import { Ballot } from "@/components/Ballot";
import { GeneratingState } from "@/components/GeneratingState";
import { OptionCard } from "@/components/OptionCard";
import { PreferenceForm } from "@/components/PreferenceForm";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError, participants, votes } from "@/lib/api";
import { STATUS, formatDateRange } from "@/lib/trip";
import { useFetch } from "@/hooks/useFetch";
import type { ParticipantBrief, ParticipantTripView } from "@/types";

function initials(p: ParticipantBrief): string {
  const parts = p.name?.split(/[\s._-]+/).filter(Boolean) ?? [];
  if (parts.length === 0) return `P${p.id.toString()}`;
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Progress({ list }: { list: ParticipantBrief[] }) {
  const done = list.filter((p) => p.preferences_submitted).length;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground tabular-nums">
        {done} of {list.length} submitted preferences
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {list.map((p) => (
          <li
            key={p.id}
            title={p.preferences_submitted ? "Submitted" : "Waiting"}
            className={`flex size-8 items-center justify-center rounded-full text-xs font-medium ${
              p.preferences_submitted
                ? "bg-success-subtle text-success"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {initials(p)}
            <span className="sr-only">{p.preferences_submitted ? " submitted" : " waiting"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Skeletons() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-5 w-1/3" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function Options({ view }: { view: ParticipantTripView }) {
  const rounds = view.voting_results?.rounds ?? [];
  const last = rounds.length ? rounds[rounds.length - 1].results : undefined;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {view.itineraries.map((o) => (
        <OptionCard key={o.id} option={o} votes={last ? (last[o.id] ?? 0) : undefined} />
      ))}
    </div>
  );
}

export default function Trip() {
  const { token = "" } = useParams<{ token: string }>();
  const location = useLocation();
  const { data, error, isLoading, refetch } = useFetch(
    () => participants.getTripView(token),
    [token],
    { poll: (d) => (d.trip.status === "GENERATING" ? 5000 : null) }
  );
  const ballotRef = useRef<HTMLElement>(null);
  const focusBallot = location.pathname.endsWith("/vote");
  const ballotShown = data?.trip.status === "VOTING";

  useEffect(() => {
    if (focusBallot && ballotShown) ballotRef.current?.focus();
  }, [focusBallot, ballotShown]);

  if (isLoading)
    return (
      <div className="mx-auto w-full max-w-3xl">
        <Skeletons />
      </div>
    );

  if (!data) {
    return (
      <div className="mx-auto w-full max-w-3xl py-4 text-center">
        <p role="alert" className="text-sm text-danger">
          {error ?? "Could not load this trip."}
        </p>
        <Link
          to="/join"
          className="mt-3 inline-block text-sm font-medium underline underline-offset-4"
        >
          Back to join page
        </Link>
      </div>
    );
  }

  const { trip, participant, participants: others } = data;
  const state = location.state as { from?: string } | null;
  const winner = data.itineraries.find((i) => i.id === trip.winner_itinerary_id);
  const dates = formatDateRange(trip.proposed_start_date, trip.proposed_end_date);

  const submitVote = async (ids: number[]) => {
    try {
      await votes.submit(trip.id, token, ids);
      toast.success(data.has_voted ? "Vote updated" : "Vote submitted");
      refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not submit your vote.");
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl animate-fade-in flex-col gap-6">
      {state?.from === "dashboard-invited" && (
        <Link
          to="/dashboard?tab=invited"
          className="inline-flex items-center gap-1 self-start text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          My trips
        </Link>
      )}

      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{trip.title}</h1>
          <Badge tone={STATUS[trip.status].tone}>{STATUS[trip.status].label}</Badge>
        </div>
        <p className="text-muted-foreground">{trip.destination || "Destination TBD"}</p>
        <Progress list={others} />
      </header>

      {(trip.status === "CREATED" || trip.status === "COLLECTING_PREFERENCES") && (
        <>
          {(trip.destination || dates || trip.notes) && (
            <section className="rounded-xl border bg-surface p-4">
              <h2 className="mb-2 text-sm font-semibold">Organizer&apos;s proposal</h2>
              <dl className="flex flex-col gap-1 text-sm">
                {trip.destination && (
                  <div>
                    <dt className="inline text-muted-foreground">Destination: </dt>
                    <dd className="inline">{trip.destination}</dd>
                  </div>
                )}
                {dates && (
                  <div>
                    <dt className="inline text-muted-foreground">Dates: </dt>
                    <dd className="inline tabular-nums">{dates}</dd>
                  </div>
                )}
                {trip.notes && (
                  <div>
                    <dt className="inline text-muted-foreground">Notes: </dt>
                    <dd className="inline whitespace-pre-line">{trip.notes}</dd>
                  </div>
                )}
              </dl>
            </section>
          )}
          {participant.preferences_submitted ? (
            <section className="flex flex-col items-center gap-2 rounded-xl border bg-surface px-5 py-10 text-center">
              <span className="flex size-10 items-center justify-center rounded-full bg-success-subtle text-success">
                <Check className="size-5" aria-hidden="true" />
              </span>
              <h2 className="text-lg font-semibold tracking-tight">Preferences submitted</h2>
              <p className="text-sm text-muted-foreground">
                Waiting for the rest of the group. We&apos;ll generate options once the organizer
                starts.
              </p>
            </section>
          ) : (
            <section className="rounded-xl border bg-surface p-4">
              <h2 className="mb-4 text-lg font-semibold tracking-tight">Your preferences</h2>
              <PreferenceForm
                token={token}
                proposedStart={trip.proposed_start_date}
                proposedEnd={trip.proposed_end_date}
                onSubmitted={refetch}
              />
            </section>
          )}
        </>
      )}

      {trip.status === "GENERATING" && <GeneratingState status="generating" />}
      {trip.status === "GENERATION_FAILED" && <GeneratingState status="failed" />}

      {ballotShown && (
        <>
          <section className="flex flex-col gap-3" aria-labelledby="options-h">
            <h2 id="options-h" className="text-lg font-semibold tracking-tight">
              Options
            </h2>
            <Options view={data} />
          </section>
          <section
            ref={ballotRef}
            tabIndex={-1}
            aria-labelledby="ballot-h"
            className="flex flex-col gap-3 outline-none"
          >
            <h2 id="ballot-h" className="text-lg font-semibold tracking-tight">
              {data.has_voted ? "Update your vote" : "Cast your vote"}
            </h2>
            <Ballot
              options={data.itineraries}
              onSubmit={submitVote}
              submitLabel={data.has_voted ? "Update vote" : "Submit vote"}
            />
          </section>
        </>
      )}

      {trip.status === "FINALIZED" && (
        <section className="flex flex-col gap-3">
          {winner ? (
            <>
              <h2 className="text-lg font-semibold tracking-tight">Your group has a winner</h2>
              <OptionCard option={winner} winner />
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold tracking-tight">Trip finalized</h2>
              {data.itineraries.length > 0 && <Options view={data} />}
            </>
          )}
        </section>
      )}
    </div>
  );
}
