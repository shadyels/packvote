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
import type { PlatformStats, PromptQuality } from "@/types";

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const flapFigure = (n: number) => (n < 10_000 ? n.toString() : compact.format(n));
const seconds = (ms: number) => (ms / 1000).toString();
const secs1 = (ms: number | null) => (ms === null ? "—" : `${(ms / 1000).toFixed(1)} s`);
const avg = (n: number | null) => (n === null ? "—" : n.toFixed(1));
const pct = (n: number | null) => (n === null ? "—" : `${(n * 100).toFixed(1)}%`);
const share = (part: number, whole: number) => (whole === 0 ? null : part / whole);
/** 4 significant digits so $0.0004 stays readable; null means unpriced. */
const usd = (n: number | null) =>
  n === null
    ? "—"
    : n === 0
      ? "$0"
      : n < 0.0001
        ? "<$0.0001"
        : `$${n.toLocaleString("en", { maximumSignificantDigits: 4 })}`;
const words = (s: string) => s.replace(/_/g, " ");
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
        <div key={label} className="flex flex-col justify-between">
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
  wrapLabels = false,
}: {
  caption: string;
  headers: string[];
  rows: ({ key: string; cells: ReactNode[] } | { key: string; group: string })[];
  empty: string;
  /** Leading columns that hold text; the rest are right-aligned figures. */
  textCols?: number;
  /** Long row labels may wrap; otherwise every cell stays on one line and the table scrolls. */
  wrapLabels?: boolean;
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
                  <th
                    key={h}
                    scope="col"
                    className={`${th} ${i === 0 ? "sticky left-0 bg-muted" : ""} ${i < textCols ? "" : "text-right"}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) =>
                "group" in r ? (
                  <tr key={r.key} className="border-t">
                    <td colSpan={headers.length} className="px-3 pt-4 pb-1.5 text-sm font-medium">
                      {r.group}
                    </td>
                  </tr>
                ) : (
                  <tr key={r.key} className="border-t">
                    {r.cells.map((c, i) => (
                      <td
                        key={i}
                        className={`px-3 py-2 ${wrapLabels && i < textCols ? "" : "whitespace-nowrap"} ${i === 0 ? "sticky left-0 bg-background" : ""} ${i < textCols ? "" : "text-right font-mono tabular-nums"}`}
                      >
                        {c}
                      </td>
                    ))}
                  </tr>
                )
              )}
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
          <tr className="border-t">
            <th scope="row" className="px-3 py-2 text-sm font-normal">
              Cost at list price
            </th>
            <td className="px-3 py-2 text-right font-mono text-sm tabular-nums">
              {usd(totals.cost_usd)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function Funnel({ totals, v }: { totals: PlatformStats["totals"]; v: PlatformStats["voting"] }) {
  const of = (n: number) => `${pct(share(n, totals.trips))} of created`;
  return (
    <BarTable
      caption="How far trips got, as a share of trips created."
      labelHeader="Stage"
      valueHeader="Trips"
      empty="No trips yet."
      rows={
        totals.trips === 0
          ? []
          : [
              { key: "created", label: "Created", value: totals.trips },
              {
                key: "voting",
                label: `Reached voting (${of(v.trips_reached_voting)})`,
                value: v.trips_reached_voting,
              },
              {
                key: "finalized",
                label: `Finalized (${of(v.finalized_trips)})`,
                value: v.finalized_trips,
              },
            ]
      }
    />
  );
}

type QualityVersion = PromptQuality["versions"][number];

const CHECK_LABELS: Record<string, string> = {
  json_valid: "JSON valid",
  time_field: "Followed its time-field instruction",
  time_slots: "Has time-of-day slots",
};
const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function Quality({ q }: { q: PromptQuality }) {
  const all = q.versions.flatMap((p) => p.checks);
  const names = [...new Set(all.map((c) => c.check))];
  const isGating = (n: string) => all.find((c) => c.check === n)?.gating ?? true;
  const criteria = [...new Set(q.versions.flatMap((p) => p.judge.map((j) => j.criterion)))];
  const row = (key: string, label: string, f: (p: QualityVersion) => string) => ({
    key,
    cells: [label, ...q.versions.map(f)],
  });
  const checkRow = (n: string) =>
    row(`check-${n}`, CHECK_LABELS[n] ?? sentence(words(n)), (p) => {
      const c = p.checks.find((x) => x.check === n);
      return c ? `${pct(c.pass_rate)} (${c.cases.toString()})` : "—";
    });
  const counted = names.filter(isGating);
  const informational = names.filter((n) => !isGating(n));
  return (
    <PlainTable
      caption={`Offline eval of ${q.cases.toString()} synthetic cases run on ${q.run_date}. Generated by ${q.model}, judged by ${q.judge_model}.`}
      headers={["Metric", ...q.versions.map((p) => p.prompt_version)]}
      empty="No eval results."
      wrapLabels
      rows={[
        row("cases", "Cases", (p) => p.cases.toString()),
        row("all", "Pass every check", (p) => pct(p.all_checks_pass_rate)),
        { key: "g-checks", group: "Checks: pass rate (applicable cases)" },
        ...counted.map(checkRow),
        ...(informational.length > 0
          ? [
              { key: "g-info", group: "Not counted in “Pass every check”" },
              ...informational.map(checkRow),
            ]
          : []),
        { key: "g-judge", group: "Judge: mean score, 1–5" },
        row("judged", "Judged cases", (p) => p.judged_cases.toString()),
        ...criteria.map((c) =>
          row(`judge-${c}`, sentence(words(c)), (p) => {
            const m = p.judge.find((j) => j.criterion === c)?.mean;
            return m == null ? "—" : m.toFixed(2);
          })
        ),
        row("overall", "Overall", (p) =>
          p.judge_overall === null ? "—" : p.judge_overall.toFixed(2)
        ),
      ]}
    />
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

function Gaps({ s }: { s: PlatformStats }) {
  const { truncated, row_cap: rowCap } = s.sampling;
  const unpriced = s.pricing.unpriced_models;
  const items = [
    "A run counts as succeeded when the AI returned a usable response, including the rare run PackVote discarded because the trip was reset while the AI was working.",
    "Latency is per AI attempt, failures included.",
    "Runs that failed outright before migration 0002 have no prompt version, so older versions' valid rate and cost leave out their worst runs.",
    `Costs are list-price equivalents as of ${s.pricing.as_of}. Actual spend on Gemini's free tier is $0.`,
    "Attempts refused by PackVote's own AI rate limiter are not logged.",
    "Emails sent are not stored.",
    "There is no finalization timestamp, so time-to-finalize cannot be shown.",
    "Deleted trips drop out of every count except AI attempts, which show as orphaned.",
  ];
  if (unpriced.length > 0)
    items.push(
      `No price on file for ${unpriced.join(", ")}; cost for ${unpriced.length === 1 ? "that model" : "those models"} is left out of every total.`
    );
  const pq = s.prompt_quality;
  if (pq) {
    items.push(
      `Prompt quality comes from ${pq.cases.toString()} synthetic offline cases, not live traffic.`
    );
    if (pq.judge_model === pq.model)
      items.push(
        "The LLM judge is the same model family grading its own output, so self-grading bias is possible."
      );
  }
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
  const round1 = v.iterations_to_finalize.find((i) => i.iterations === 1)?.trips ?? 0;
  const rounds = v.iterations_to_finalize.reduce((a, i) => a + i.iterations * i.trips, 0);
  return (
    <>
      <Section title="Totals">
        <Totals totals={s.totals} />
      </Section>

      <Section title="Conversion funnel">
        <Funnel totals={s.totals} v={v} />
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

      <Section title="Voting">
        <Figures
          items={[
            ["Avg participants per trip", avg(v.avg_participants_per_trip)],
            ["Avg votes per trip", avg(v.avg_votes_per_trip)],
            ["Finalized in round 1", pct(share(round1, v.finalized_trips))],
            [
              "Mean rounds to finalize",
              avg(v.finalized_trips === 0 ? null : rounds / v.finalized_trips),
            ],
            ["Cost per finalized trip (list price)", usd(v.cost_per_finalized_trip_usd)],
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

      <Section title="Generation">
        <Figures
          items={[
            ["Valid rate", pct(g.valid_rate)],
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
          headers={[
            "Model",
            "Provider",
            "Attempts",
            "Valid",
            "Tokens in",
            "Tokens out",
            "Cost (list price)",
          ]}
          empty="No AI attempts yet."
          textCols={2}
          rows={s.by_model.map((m) => ({
            key: JSON.stringify([m.provider, m.model]),
            cells: [
              m.model,
              m.provider,
              m.attempts.toLocaleString(),
              m.valid_attempts.toLocaleString(),
              m.tokens_in.toLocaleString(),
              m.tokens_out.toLocaleString(),
              usd(m.cost_usd),
            ],
          }))}
        />
      </Section>

      <Section title="By prompt version">
        <PlainTable
          caption="Generations and itineraries count successful runs; attempts, latency and cost include failures. Cost is at list price."
          headers={[
            "Prompt version",
            "Generations",
            "Itineraries",
            "Attempts",
            "Valid rate",
            "p50 latency",
            "p95 latency",
            "Tokens / itinerary",
            "Cost / itinerary",
          ]}
          empty="No successful generations yet."
          rows={s.by_prompt_version.map((p) => ({
            key: p.prompt_version ?? "unversioned",
            cells: [
              p.prompt_version ?? "unversioned",
              p.successful_generations.toLocaleString(),
              p.itineraries.toLocaleString(),
              p.attempts.toLocaleString(),
              pct(p.valid_rate),
              secs1(p.latency_p50_ms),
              secs1(p.latency_p95_ms),
              p.tokens_per_itinerary === null
                ? "—"
                : Math.round(p.tokens_per_itinerary).toLocaleString(),
              usd(p.cost_per_itinerary_usd),
            ],
          }))}
        />
      </Section>

      {s.prompt_quality && (
        <Section title="Prompt quality">
          <Quality q={s.prompt_quality} />
        </Section>
      )}

      <Section title="What this measures">
        <Gaps s={s} />
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
