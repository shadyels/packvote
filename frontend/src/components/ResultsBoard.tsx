import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { optionTitle } from "@/components/OptionCard";
import { Button } from "@/components/ui/Button";
import { FlapWord, StatusFlap } from "@/components/ui/Flap";
import { cn, flapText, prefersReducedMotion, type Tone } from "@/lib/trip";
import type { Itinerary, VotingResults } from "@/types";

export type BoardStatus = "BOARDING" | "ELIMINATED" | "RUNNER-UP" | "TIED";

export interface BoardRow {
  id: number;
  title: string;
  flap: string;
  /** One entry per round; null = the option was already out. */
  counts: (number | null)[];
  /** round_number in which the option was eliminated. */
  outRound: number | null;
  status: BoardStatus;
}

/** Rows of the runoff board: every option of round 1, best first. [] when nobody has voted. */
export function boardRows(results: VotingResults, options: Itinerary[]): BoardRow[] {
  const { rounds } = results;
  if (rounds.length === 0) return [];
  const last = rounds[rounds.length - 1];
  return Object.keys(rounds[0].results)
    .map(Number)
    .map((id) => {
      const option = options.find((o) => o.id === id);
      const title = option ? optionTitle(option) : `#${id.toString()}`;
      const outRound = rounds.find((r) => r.eliminated_option_id === id)?.round_number ?? null;
      const status: BoardStatus =
        outRound !== null
          ? "ELIMINATED"
          : last.winner_id === id
            ? "BOARDING"
            : last.winner_id === null
              ? "TIED"
              : "RUNNER-UP";
      return {
        id,
        title,
        flap: flapText(title),
        counts: rounds.map((r) => r.results[id] ?? null),
        outRound,
        status,
      };
    })
    .sort((a, b) => (b.counts[0] ?? 0) - (a.counts[0] ?? 0) || a.id - b.id);
}

const PHASE_MS = 650;

const th = "px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase";
const cell = "px-3 py-3 max-md:p-0";
const label =
  "max-md:flex max-md:items-baseline max-md:gap-1.5 max-md:before:text-[0.7rem] max-md:before:opacity-70 max-md:before:content-[attr(data-label)]";

export function ResultsBoard({
  results,
  options,
  final,
  playOnMount = false,
}: {
  results: VotingResults;
  options: Itinerary[];
  /** True once the trip is finalized: the leader boards (yellow row). False = provisional "Leading". */
  final: boolean;
  /** Replay the runoff on first mount; by default the board appears already settled. */
  playOnMount?: boolean;
}) {
  const [reduced] = useState(prefersReducedMotion);
  const rounds = results.rounds;
  const FINAL = rounds.length * 2;
  // Infinity = settled (the default); a play counts up from 0.
  const [phase, setPhase] = useState(Infinity);
  // 0 until the first play; flips only run once something has played.
  const [run, setRun] = useState(0);
  const timers = useRef<number[]>([]);
  const runId = useRef(0);

  const stop = useCallback(() => {
    runId.current += 1;
    timers.current.forEach(window.clearTimeout);
    timers.current = [];
  }, []);

  const roundCount = rounds.length;
  const play = useCallback(() => {
    stop();
    if (reduced || roundCount === 0) return;
    const id = runId.current;
    setRun(id);
    setPhase(0);
    timers.current = Array.from({ length: roundCount * 2 }, (_, i) =>
      window.setTimeout(
        () => {
          if (id === runId.current) setPhase(i + 1);
        },
        (i + 1) * PHASE_MS
      )
    );
  }, [reduced, roundCount, stop]);

  // Mount: settled unless asked to play. Unmount: drop pending timers.
  useLayoutEffect(() => {
    if (playOnMount) play();
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount only
  }, []);

  // New votes after mount replay the runoff. Identical polled data has the same key.
  const key = JSON.stringify(rounds);
  const seen = useRef(key);
  useLayoutEffect(() => {
    if (seen.current === key) return;
    seen.current = key;
    play();
  }, [key, play]);

  const rows = boardRows(results, options);
  const settled = phase >= FINAL;
  const animate = run > 0 && !reduced;
  const ballots =
    rounds.length > 0 ? Object.values(rounds[0].results).reduce((a, n) => a + n, 0) : 0;

  const voteWinner = rounds.length > 0 ? rounds[rounds.length - 1].winner_id : null;
  const overridden = results.winner_id !== null && results.winner_id !== voteWinner;
  const overrideTitle = (() => {
    if (!overridden) return null;
    const o = options.find((x) => x.id === results.winner_id);
    return o ? optionTitle(o) : `#${String(results.winner_id)}`;
  })();

  // Not-yet-revealed content is faded, never removed, so assistive tech always sees the final state.
  const reveal = (on: boolean, node: ReactNode) => (
    <span className={cn("inline-block", !on && "opacity-0", on && animate && "animate-flip")}>
      {node}
    </span>
  );

  // The organizer's pick takes the yellow row and Boarding; the vote's winner reads "Won vote".
  const override = overridden && final;

  const statusFlap = (row: BoardRow): { tone: Tone; text: string } => {
    if (override) {
      if (row.id === results.winner_id) return { tone: "success", text: "Boarding" };
      if (row.status === "BOARDING") return { tone: "muted", text: "Won vote" };
    }
    switch (row.status) {
      case "ELIMINATED":
        return { tone: "danger", text: "Eliminated" };
      case "BOARDING":
        return final ? { tone: "success", text: "Boarding" } : { tone: "flap", text: "Leading" };
      case "TIED":
        return { tone: "muted", text: "Tied" };
      case "RUNNER-UP":
        return { tone: "muted", text: "Runner-up" };
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {overrideTitle !== null && (
        <p className="text-sm font-medium">{`Organizer finalized ${overrideTitle}`}</p>
      )}
      {rounds.length === 0 ? (
        <EmptyState title="No votes yet" text="The board fills in as ballots arrive." />
      ) : (
        <div className="overflow-x-auto rounded-sm border bg-surface">
          <table role="table" className="w-full border-collapse text-left max-md:block">
            <caption className="caption-top border-b px-3 py-3 text-left font-mono text-sm max-md:block">
              {`${ballots.toString()} ballot${ballots === 1 ? "" : "s"} · Iteration ${results.iteration_number.toString()}`}
            </caption>
            <thead role="rowgroup" className="bg-muted text-muted-foreground max-md:sr-only">
              <tr role="row">
                <th role="columnheader" scope="col" className={th}>
                  Option
                </th>
                {rounds.map((r) => (
                  <th
                    key={r.round_number}
                    role="columnheader"
                    scope="col"
                    className={cn(th, "md:text-right")}
                  >
                    {`R${r.round_number.toString()}`}
                  </th>
                ))}
                <th role="columnheader" scope="col" className={th}>
                  Status
                </th>
              </tr>
            </thead>
            <tbody role="rowgroup" className="max-md:block">
              {rows.map((row) => {
                const isPick = override && row.id === results.winner_id;
                const yellow = settled && (override ? isPick : final && row.status === "BOARDING");
                const flap = statusFlap(row);
                const statusOn =
                  row.outRound !== null && !isPick ? phase >= row.outRound * 2 : settled;
                return (
                  <tr
                    key={row.id}
                    role="row"
                    className={cn(
                      "border-t transition-colors duration-300 max-md:flex max-md:flex-wrap max-md:items-center max-md:gap-x-4 max-md:gap-y-2 max-md:p-3",
                      yellow && "bg-accent text-accent-foreground"
                    )}
                  >
                    <th
                      role="rowheader"
                      scope="row"
                      className={cn(cell, "text-left max-md:basis-full")}
                    >
                      <div className="flex flex-col gap-1">
                        <FlapWord text={row.flap} label={null} size="board" inverted={yellow} />
                        <span
                          className={cn(
                            "text-sm font-normal break-words max-md:text-xs",
                            row.title.toLowerCase() === row.flap.toLowerCase() && "sr-only"
                          )}
                        >
                          {row.title}
                        </span>
                      </div>
                    </th>
                    {row.counts.map((count, i) => (
                      <td
                        key={rounds[i].round_number}
                        role="cell"
                        data-label={`R${rounds[i].round_number.toString()}`}
                        className={cn(cell, label, "font-mono tabular-nums md:text-right")}
                      >
                        {reveal(
                          phase >= i * 2 + 1,
                          count === null ? (
                            <>
                              <span aria-hidden="true">–</span>
                              <span className="sr-only">out</span>
                            </>
                          ) : (
                            count
                          )
                        )}
                      </td>
                    ))}
                    <td role="cell" className={cn(cell, "max-md:basis-full")}>
                      {reveal(statusOn, <StatusFlap tone={flap.tone}>{flap.text}</StatusFlap>)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!reduced && (
            <div className="flex justify-end border-t p-2">
              <Button variant="ghost" size="sm" onClick={play}>
                <RotateCcw className="size-4" aria-hidden="true" />
                Replay
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
