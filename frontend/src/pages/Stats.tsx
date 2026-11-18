import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { BarTable } from "@/components/stats/BarTable";
import { DailyChart } from "@/components/stats/DailyChart";
import { EmptyState } from "@/components/EmptyState";
import { Button, buttonClass } from "@/components/ui/Button";
import { FlapWord } from "@/components/ui/Flap";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAuth } from "@/hooks/useAuth";
import { useFetch } from "@/hooks/useFetch";
import { stats } from "@/lib/api";
import { STATUS } from "@/lib/trip";
import type { PlatformStats } from "@/types";

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const flapFigure = (n: number) => (n < 10_000 ? n.toString() : compact.format(n));
const seconds = (ms: number) => (ms / 1000).toString();
const secs1 = (ms: number | null) => (ms === null ? "—" : `${(ms / 1000).toFixed(1)} s`);
const avg = (n: number | null) => (n === null ? "—" : n.toFixed(1));
const plural = (n: number, one: string, many: string) =>
  `${n.toLocaleString()} ${n === 1 ? one : many}`;

const th = "px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase";

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = `stats-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="mt-10 border-t-2 border-foreground pt-4">
      <h2 id={id} className="mb-4 text-lg font-semibold">
        {title}
      </h2>
      <div className="space-y-6">{children}</div>
    </section>
  );
}

function Figures({ items }: { items: [string, string][] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3 md:grid-cols-5">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-sm text-muted-foreground">{label}</dt>
          <dd className="font-mono text-2xl font-medium tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function PlainTable({
  caption,
  headers,
  rows,
  empty,
  textCols = 1,
}: {
  caption: string;
  headers: string[];
  rows: { key: string; cells: ReactNode[] }[];
  empty: string;
  /** Leading columns that hold text; the rest are right-aligned figures. */
  textCols?: number;
}) {
  return (
    <div>
      <p className="mb-2 text-sm text-muted-foreground">{caption}</p>
      {rows.length === 0 ? (
        <p className="border-t py-3 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div
          role="region"
          aria-label={caption}
          tabIndex={0}
          className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-accent-ink"
        >
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                {headers.map((h, i) => (
                  <th key={h} scope="col" className={`${th} ${i < textCols ? "" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-t">
                  {r.cells.map((c, i) => (
                    <td
                      key={i}
                      className={`px-3 py-2 ${i < textCols ? "" : "text-right font-mono tabular-nums"}`}
                    >
                      {c}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Totals({ totals }: { totals: PlatformStats["totals"] }) {
  const rows: [string, number][] = [
    ["Trips", totals.trips],
    ["Users", totals.users],
    ["Participants", totals.participants],
    ["Votes", totals.votes],
    ["Itineraries", totals.itineraries],
    ["AI attempts", totals.ai_attempts],
    ["Tokens in", totals.tokens_in],
    ["Tokens out", totals.tokens_out],
  ];
  return (
    <div className="overflow-x-auto rounded-sm border bg-surface">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">Totals</caption>
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th scope="col" className={th}>
              Metric
            </th>
            <th scope="col" className={`${th} text-right`}>
              Count
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, n]) => (
            <tr key={label} className="border-t">
              <th scope="row" className="px-3 py-2 text-sm font-normal">
                {label}
              </th>
              <td className="px-3 py-2">
                <div className="flex justify-end">
                  <FlapWord text={flapFigure(n)} label={n.toLocaleString()} size="sm" />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading stats" className="mt-10 space-y-4">
      <Skeleton className="h-48" />
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
    </div>
  );
}

function Gaps({ truncated, rowCap }: { truncated: boolean; rowCap: number }) {
  const items = [
    "A run counts as succeeded when the AI returned a usable response, including the rare run PackVote discarded because the trip was reset while the AI was working.",
    "Latency is per AI attempt, failures included.",
    "Failed AI attempts carry no prompt version.",
    "No cost data: tokens only.",
    "Attempts refused by PackVote's own AI rate limiter are not logged.",
    "Emails sent are not stored.",
    "There is no finalization timestamp, so time-to-finalize cannot be shown.",
    "Deleted trips drop out of every count except AI attempts, which show as orphaned.",
  ];
  if (truncated)
    items.push(`Latency and daily activity use the most recent ${rowCap.toLocaleString()} rows.`);
  return (
    <ul className="max-w-prose list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
      {items.map((t) => (
        <li key={t}>{t}</li>
      ))}
    </ul>
  );
}

function Report({ s }: { s: PlatformStats }) {
  const { isAuthenticated } = useAuth();
  const g = s.generation;
  const v = s.voting;
  return (
    <>
      <Section title="Totals">
        <Totals totals={s.totals} />
      </Section>

      <Section title="Trips by current status">
        <BarTable
          caption="Where trips are now, not history."
          labelHeader="Status"
          valueHeader="Trips"
          empty="No trips yet."
          rows={s.funnel.map((f) => ({
            key: f.status,
            label: STATUS[f.status].label,
            value: f.trips,
          }))}
        />
      </Section>

      <Section title="Generation">
        <Figures
          items={[
            ["Valid rate", g.valid_rate === null ? "—" : `${(g.valid_rate * 100).toFixed(1)}%`],
            ["Runs succeeded", `${g.runs_succeeded.toLocaleString()} / ${g.runs.toLocaleString()}`],
            ["Median latency", secs1(g.latency.p50_ms)],
            ["95th percentile latency", secs1(g.latency.p95_ms)],
            ["Orphaned attempts", g.orphaned_attempts.toLocaleString()],
          ]}
        />
        <BarTable
          caption={`Latency per attempt, failures included (${g.latency.sample_size.toLocaleString()} sampled).`}
          labelHeader="Latency"
          valueHeader="Attempts"
          empty="No attempts yet."
          rows={
            g.attempts === 0
              ? []
              : g.latency.histogram.map((b) => ({
                  key: b.min_ms.toString(),
                  label:
                    b.max_ms === null
                      ? `${seconds(b.min_ms)} s+`
                      : `${seconds(b.min_ms)}–${seconds(b.max_ms)} s`,
                  value: b.attempts,
                }))
          }
        />
        <BarTable
          caption="Attempts needed per generation run."
          labelHeader="Attempts"
          valueHeader="Runs"
          empty="No generation runs yet."
          rows={g.attempts_per_run.map((a) => ({
            key: a.attempts.toString(),
            label: plural(a.attempts, "attempt", "attempts"),
            value: a.runs,
          }))}
        />
        <BarTable
          caption="How each AI attempt ended."
          labelHeader="Finish reason"
          valueHeader="Attempts"
          empty="No attempts yet."
          rows={g.finish_reasons.map((f) => ({
            key: f.finish_reason === null ? "__null__" : f.finish_reason,
            label: f.finish_reason ?? "none (request failed)",
            value: f.attempts,
          }))}
        />
      </Section>

      <Section title="By model">
        <PlainTable
          caption="AI attempts per provider and model."
          headers={["Provider", "Model", "Attempts", "Valid", "Tokens in", "Tokens out"]}
          empty="No AI attempts yet."
          textCols={2}
          rows={s.by_model.map((m) => ({
            key: JSON.stringify([m.provider, m.model]),
            cells: [
              m.provider,
              m.model,
              m.attempts.toLocaleString(),
              m.valid_attempts.toLocaleString(),
              m.tokens_in.toLocaleString(),
              m.tokens_out.toLocaleString(),
            ],
          }))}
        />
      </Section>

      <Section title="By prompt version">
        <PlainTable
          caption="Successful generations only."
          headers={["Prompt version", "Generations", "Itineraries"]}
          empty="No successful generations yet."
          rows={s.by_prompt_version.map((p) => ({
            key: p.prompt_version ?? "unversioned",
            cells: [
              p.prompt_version ?? "unversioned",
              p.successful_generations.toLocaleString(),
              p.itineraries.toLocaleString(),
            ],
          }))}
        />
      </Section>

      <Section title="Last 30 days">
        <DailyChart
          title="Trips created per day"
          days={s.activity}
          value={(d) => d.trips}
          unit="trips"
        />
        <DailyChart
          title="Tokens per day (in and out)"
          days={s.activity}
          value={(d) => d.tokens_in + d.tokens_out}
          unit="tokens"
        />
      </Section>

      <Section title="Voting">
        <Figures
          items={[
            ["Avg participants per trip", avg(v.avg_participants_per_trip)],
            ["Avg votes per trip", avg(v.avg_votes_per_trip)],
            ["Finalized trips", v.finalized_trips.toLocaleString()],
            ["Trips that reached voting", v.trips_reached_voting.toLocaleString()],
          ]}
        />
        <BarTable
          caption="Rounds of options before finalizing."
          labelHeader="Rounds"
          valueHeader="Trips"
          empty="No finalized trips yet."
          rows={v.iterations_to_finalize.map((i) => ({
            key: i.iterations.toString(),
            label: plural(i.iterations, "round", "rounds"),
            value: i.trips,
          }))}
        />
      </Section>

      <Section title="What this measures">
        <Gaps truncated={s.sampling.truncated} rowCap={s.sampling.row_cap} />
      </Section>

      <div className="mt-10 border-t-2 border-foreground pt-6">
        <Link to={isAuthenticated ? "/dashboard" : "/login"} className={buttonClass("primary")}>
          {isAuthenticated ? "Go to dashboard" : "Plan a trip"}
        </Link>
      </div>
    </>
  );
}

export default function Stats() {
  const { data, error, isLoading, refetch } = useFetch(() => stats.get(), []);

  return (
    <div>
      <h1 className="text-2xl font-semibold">Platform stats</h1>
      {data && (
        <p className="mt-1 text-sm text-muted-foreground">
          Live aggregates, refreshed at most once a minute. Updated{" "}
          {new Date(data.generated_at).toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
          })}
          .
        </p>
      )}
      {isLoading && <Loading />}
      {error && !data && (
        <div className="mt-10 space-y-4">
          <EmptyState title="Couldn't load the stats" text={error} />
          <Button variant="secondary" size="sm" onClick={refetch}>
            Try again
          </Button>
        </div>
      )}
      {data && <Report s={data} />}
    </div>
  );
}
