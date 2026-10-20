import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, Copy, Layers, Mail, Users, Vote, X } from "lucide-react";
import { Ballot } from "@/components/Ballot";
import { EmptyState } from "@/components/EmptyState";
import { GeneratingState } from "@/components/GeneratingState";
import { OptionCard, optionTitle } from "@/components/OptionCard";
import { Results } from "@/components/Results";
import { TripForm } from "@/components/TripForm";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/Tabs";
import { useAuth } from "@/hooks/useAuth";
import { useFetch } from "@/hooks/useFetch";
import { admin, ApiError, itineraries, participants, trips, votes } from "@/lib/api";
import { STATUS, formatDateRange } from "@/lib/trip";
import type { Itinerary, Participant, Trip, VotingResults } from "@/types";

const TABS = ["overview", "participants", "options", "results"] as const;
type Tab = (typeof TABS)[number];

const GENERATING_POLL_MS = 5000;
const WAITING_POLL_MS = 15000;
const WAITING_STATUSES = ["CREATED", "COLLECTING_PREFERENCES", "VOTING"];
const HAS_RESULTS = ["VOTING", "FINALIZED"];

function pollDelay({ trip }: Data): number | null {
  if (trip.status === "GENERATING") return GENERATING_POLL_MS;
  return WAITING_STATUSES.includes(trip.status) ? WAITING_POLL_MS : null;
}
interface Data {
  trip: Trip;
  people: Participant[];
  options: Itinerary[];
  results: VotingResults | null;
}

// Any failed sub-request rejects the whole load, so a poll keeps the last good data.
async function load(tripId: number): Promise<Data> {
  const [trip, people, options] = await Promise.all([
    trips.get(tripId),
    participants.listByTrip(tripId),
    itineraries.getByTrip(tripId),
  ]);
  const results = HAS_RESULTS.includes(trip.status) ? await votes.getResults(tripId) : null;
  return { trip, people, options, results };
}

const errMsg = (err: unknown, fallback: string) =>
  err instanceof ApiError ? err.message : fallback;

function resendToast({ sent, failed }: { sent: number; failed: number }) {
  if (failed === 0) toast.success(`Sent ${sent.toString()} email${sent === 1 ? "" : "s"}`);
  else toast.error(`Sent ${sent.toString()}, ${failed.toString()} failed`);
}

export default function TripDetail() {
  const id = Number(useParams().tripId);
  const navigate = useNavigate();
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const tab: Tab = TABS.find((t) => t === requested) ?? "overview";

  const { data, error, isLoading, refetch } = useFetch(() => load(id), [id], { poll: pollDelay });

  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [pick, setPick] = useState("");

  if (isLoading) {
    return (
      <div role="status" aria-label="Loading trip" className="flex flex-col gap-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-9 w-72 max-w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-start gap-4">
        <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
          Back to dashboard
        </Link>
        <div
          role="alert"
          className="flex w-full items-center justify-between gap-3 rounded-xl border border-danger/30 bg-danger-subtle px-4 py-3 text-sm text-danger"
        >
          <span>{error ?? "Failed to load trip."}</span>
          <Button variant="secondary" size="sm" onClick={refetch}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const { trip, people, options, results } = data;
  const status = trip.status;
  const isVotingPhase = status === "VOTING";
  const current = options.filter((o) => o.iteration_number === trip.current_iteration);
  const me = people.find((p) => p.email === user?.email);
  const done = people.filter((p) =>
    isVotingPhase ? p.has_voted_current_iteration : p.preferences_submitted
  ).length;
  const dates = formatDateRange(trip.proposed_start_date, trip.proposed_end_date);
  const picked = current.find((o) => String(o.id) === pick);

  // One shared busy flag: the running action shows a spinner, every other action is disabled.
  const run = async (key: string, action: () => Promise<void>, fallback: string) => {
    setBusy(key);
    try {
      await action();
    } catch (err) {
      toast.error(errMsg(err, fallback));
    } finally {
      setBusy(null);
    }
  };

  const act = (key: string, call: () => Promise<unknown>, okMsg: string, failMsg: string) =>
    run(
      key,
      async () => {
        await call();
        toast.success(okMsg);
        refetch();
      },
      failMsg
    );

  const generate = () =>
    act(
      "generate",
      () => trips.triggerGeneration(trip.id),
      "Generation started — options will appear shortly.",
      "Could not start generation."
    );

  const finalize = async () => {
    setFinalizing(false);
    await act(
      "finalize",
      () => trips.pickWinner(trip.id, Number(pick)),
      "Winner selected — trip finalized",
      "Could not finalize the trip."
    );
  };

  const newRound = () =>
    act(
      "round",
      async () => {
        await trips.triggerNewIteration(trip.id);
        setPick("");
      },
      "New round started.",
      "Could not start a new round."
    );

  const remove = async () => {
    setBusy("delete");
    try {
      await trips.delete(trip.id);
      toast.success("Trip deleted.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(errMsg(err, "Could not delete the trip."));
      setDeleting(false);
      setBusy(null);
    }
  };

  const resend = (key: string, send: () => Promise<{ sent: number; failed: number }>) =>
    run(
      key,
      async () => {
        resendToast(await send());
      },
      "Could not send emails."
    );

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(trip.trip_code);
      toast.success("Trip code copied.");
    } catch {
      toast.error("Could not copy the code.");
    }
  };

  const voted = people.filter((p) => p.has_voted_current_iteration).length;
  const waiting = people.length - voted;
  const winner = options.find((o) => o.id === trip.winner_itinerary_id);
  const lastRound = results?.rounds[results.rounds.length - 1];
  const groups = [...new Set(options.map((o) => o.iteration_number))].sort((a, b) => b - a);

  return (
    <div>
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to dashboard
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{trip.title}</h1>
        <Badge tone={STATUS[status].tone}>{STATUS[status].label}</Badge>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 text-sm text-muted-foreground">
        <span>{trip.destination || "Surprise me"}</span>
        {error && (
          <span role="status" className="text-warning">
            Couldn&apos;t refresh. Showing the last loaded data.
          </span>
        )}
        <button
          type="button"
          aria-label={`Copy trip code ${trip.trip_code}`}
          onClick={() => {
            void copyCode();
          }}
          className="inline-flex min-h-11 items-center gap-1.5 font-mono hover:text-foreground"
        >
          {trip.trip_code}
          <Copy className="size-3.5" aria-hidden="true" />
        </button>
      </div>

      <Tabs
        className="mt-4"
        value={tab}
        onValueChange={(v) => {
          setParams({ tab: String(v) }, { replace: true });
        }}
      >
        <TabsList>
          <TabsTab value="overview">Overview</TabsTab>
          {/* Counts hide below sm so four tabs fit at 375px; display:none keeps label = accessible name. */}
          <TabsTab value="participants">
            People<span className="hidden sm:inline"> ({people.length})</span>
          </TabsTab>
          <TabsTab value="options">
            Options<span className="hidden sm:inline"> ({options.length})</span>
          </TabsTab>
          <TabsTab value="results">Results</TabsTab>
        </TabsList>

        <TabsPanel value="overview" className="flex flex-col gap-6 pt-5">
          <dl className="grid grid-cols-2 gap-4 rounded-xl border bg-surface p-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Dates</dt>
              <dd className="mt-0.5 font-medium">{dates ?? "Flexible"}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Iteration</dt>
              <dd className="mt-0.5 font-medium tabular-nums">
                {trip.current_iteration} / {trip.max_iterations}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Options per round</dt>
              <dd className="mt-0.5 font-medium tabular-nums">{trip.num_options}</dd>
            </div>
            {trip.notes && (
              <div className="col-span-2 sm:col-span-3">
                <dt className="text-muted-foreground">Notes</dt>
                <dd className="mt-0.5 whitespace-pre-wrap">{trip.notes}</dd>
              </div>
            )}
          </dl>

          {(status === "CREATED" || status === "COLLECTING_PREFERENCES") && (
            <div className="flex flex-col items-start gap-2">
              <div className="flex flex-wrap gap-2">
                <Button
                  loading={busy === "generate"}
                  disabled={busy !== null}
                  onClick={() => {
                    void generate();
                  }}
                >
                  Generate options
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() => {
                    setEditing(true);
                  }}
                >
                  Edit trip
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                You can generate before everyone has responded.
              </p>
            </div>
          )}

          {status === "GENERATING" && <GeneratingState status="generating" />}

          {status === "GENERATION_FAILED" && (
            <div className="flex flex-col gap-3">
              <GeneratingState
                status="failed"
                error={trip.generation_error}
                retrying={busy === "generate"}
                onRetry={() => {
                  void generate();
                }}
              />
              <Button
                variant="secondary"
                className="self-start"
                disabled={busy !== null}
                onClick={() => {
                  setEditing(true);
                }}
              >
                Edit trip
              </Button>
            </div>
          )}

          {isVotingPhase && (
            <section aria-label="Finish voting" className="flex flex-col gap-4">
              {current.length > 0 && me && (
                <div className="rounded-xl border bg-surface p-4">
                  <h2 className="text-sm font-semibold">Your vote</h2>
                  {me.has_voted_current_iteration ? (
                    <p className="mt-2 flex items-center gap-2 text-sm text-success">
                      <Check className="size-4" aria-hidden="true" />
                      Your vote is in
                      <span className="text-muted-foreground">
                        {waiting === 0
                          ? "All participants have voted."
                          : `Waiting on ${waiting.toString()} more.`}
                      </span>
                    </p>
                  ) : (
                    <div className="mt-3">
                      <Ballot
                        options={current}
                        submitLabel="Submit vote"
                        onSubmit={(ids) =>
                          act(
                            "vote",
                            () => votes.adminVote(trip.id, ids),
                            "Vote submitted",
                            "Could not submit your vote."
                          )
                        }
                      />
                    </div>
                  )}
                </div>
              )}

              <div className="rounded-xl border bg-surface p-4">
                <h2 className="text-sm font-semibold">Pick the winner</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Skip the vote and finalize an option yourself.
                </p>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <Select
                    aria-label="Winning option"
                    value={pick}
                    onChange={(e) => {
                      setPick(e.target.value);
                      setFinalizing(false);
                    }}
                  >
                    <option value="">Choose an option</option>
                    {current.map((o) => (
                      <option key={o.id} value={o.id}>
                        {optionTitle(o)}
                      </option>
                    ))}
                  </Select>
                  <Button
                    className="sm:shrink-0"
                    loading={busy === "finalize"}
                    disabled={busy !== null || !picked}
                    onClick={() => {
                      setFinalizing(true);
                    }}
                  >
                    Finalize
                  </Button>
                </div>
              </div>

              {trip.current_iteration < trip.max_iterations && (
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    variant="secondary"
                    loading={busy === "round"}
                    disabled={busy !== null}
                    onClick={() => {
                      void newRound();
                    }}
                  >
                    Start new iteration
                  </Button>
                  <span className="text-sm text-muted-foreground tabular-nums">
                    Iteration {trip.current_iteration + 1} of {trip.max_iterations} max
                  </span>
                </div>
              )}
            </section>
          )}

          {status === "FINALIZED" && (
            <p className="flex items-center gap-2 rounded-xl bg-success-subtle px-4 py-3 text-sm font-medium text-success">
              <Check className="size-4" aria-hidden="true" />
              Trip finalized
              {winner && `: ${optionTitle(winner)}`}
            </p>
          )}

          {status !== "GENERATING" && (
            <section
              aria-label="Danger zone"
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-danger/30 p-4"
            >
              <div>
                <h2 className="text-sm font-semibold text-danger">Delete trip</h2>
                <p className="text-sm text-muted-foreground">This cannot be undone.</p>
              </div>
              <Button
                variant="danger"
                disabled={busy !== null}
                onClick={() => {
                  setDeleting(true);
                }}
              >
                Delete trip
              </Button>
            </section>
          )}
        </TabsPanel>

        <TabsPanel value="participants">
          {people.length === 0 ? (
            <EmptyState icon={Users} title="No participants yet" text="Nobody has been invited." />
          ) : (
            <div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium tabular-nums">
                  {done} of {people.length} {isVotingPhase ? "votes" : "preferences"} submitted
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  loading={busy === "resend-all"}
                  disabled={busy !== null}
                  onClick={() => {
                    void resend("resend-all", () => admin.resendAll(trip.id));
                  }}
                >
                  <Mail className="size-4" aria-hidden="true" />
                  Resend all
                </Button>
              </div>
              <ul className="mt-3 divide-y overflow-hidden rounded-xl border">
                {people.map((p) => {
                  const ok = isVotingPhase
                    ? p.has_voted_current_iteration
                    : p.preferences_submitted;
                  return (
                    <li key={p.id} className="flex items-center gap-3 px-4 py-3">
                      {ok ? (
                        <Check className="size-4 shrink-0 text-success" aria-hidden="true" />
                      ) : (
                        <X className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      )}
                      <span className="sr-only">{ok ? "Submitted" : "Pending"}</span>
                      <div className="min-w-0 flex-1">
                        <p className="flex items-center gap-2 text-sm font-medium">
                          <span className="truncate">{p.name || p.email}</span>
                          {p.email === user?.email && <Badge>Organizer</Badge>}
                        </p>
                        {p.name && (
                          <p className="truncate text-xs text-muted-foreground">{p.email}</p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Resend email to ${p.email}`}
                        loading={busy === `resend-${p.id.toString()}`}
                        disabled={busy !== null}
                        onClick={() => {
                          void resend(`resend-${p.id.toString()}`, () =>
                            admin.resendOne(trip.id, p.id)
                          );
                        }}
                      >
                        Resend
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </TabsPanel>

        <TabsPanel value="options" className="flex flex-col gap-8 pt-5">
          {options.length === 0 ? (
            <EmptyState
              icon={Layers}
              title="No options yet"
              text="Generate options once your group has responded."
            />
          ) : (
            groups.map((iteration) => (
              <section key={iteration} aria-label={`Iteration ${iteration.toString()}`}>
                <h2 className="mb-3 text-sm font-semibold">Iteration {iteration}</h2>
                <div className="grid gap-4 md:grid-cols-2">
                  {options
                    .filter((o) => o.iteration_number === iteration)
                    .sort(
                      (a, b) =>
                        Number(b.id === trip.winner_itinerary_id) -
                        Number(a.id === trip.winner_itinerary_id)
                    )
                    .map((o) => (
                      <OptionCard
                        key={o.id}
                        option={o}
                        votes={
                          results?.iteration_number === iteration
                            ? lastRound?.results[o.id]
                            : undefined
                        }
                        winner={o.id === trip.winner_itinerary_id}
                        dimmed={
                          trip.winner_itinerary_id !== null && o.id !== trip.winner_itinerary_id
                        }
                      />
                    ))}
                </div>
              </section>
            ))
          )}
        </TabsPanel>

        <TabsPanel value="results">
          {results && results.rounds.length > 0 ? (
            <Results results={results} options={current} />
          ) : (
            <EmptyState icon={Vote} title="No votes yet" text="No votes recorded yet." />
          )}
        </TabsPanel>
      </Tabs>

      <Dialog open={editing} onOpenChange={setEditing} title="Edit trip">
        <TripForm
          trip={trip}
          onCancel={() => {
            setEditing(false);
          }}
          onDone={() => {
            setEditing(false);
            toast.success("Trip updated.");
            refetch();
          }}
        />
      </Dialog>

      <Dialog
        open={finalizing && !!picked}
        onOpenChange={setFinalizing}
        title={`Finalize "${picked ? optionTitle(picked) : ""}"?`}
        description="This ends voting for everyone and can't be undone."
      >
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              setFinalizing(false);
            }}
          >
            Cancel
          </Button>
          <Button
            disabled={busy !== null}
            onClick={() => {
              void finalize();
            }}
          >
            Confirm
          </Button>
        </div>
      </Dialog>

      <Dialog
        open={deleting}
        onOpenChange={setDeleting}
        title={`Delete "${trip.title}"?`}
        description="This will permanently delete this trip, all participants, preferences, itineraries, and voting data."
      >
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              setDeleting(false);
            }}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={busy === "delete"}
            onClick={() => {
              void remove();
            }}
          >
            Delete trip
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
