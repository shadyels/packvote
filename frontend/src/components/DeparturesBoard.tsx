import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { FlapWord } from "@/components/ui/Flap";
import { useFlip } from "@/hooks/useFlip";
import { cn, prefersReducedMotion } from "@/lib/trip";

type Option = "dolomites" | "lisbon" | "naxos";
const OPTIONS: Option[] = ["dolomites", "lisbon", "naxos"];
const NAMES: Record<Option, string> = { dolomites: "Dolomites", lisbon: "Lisbon", naxos: "Naxos" };

// Each sample friend's full ranking, best first. The board is derived from these.
const BALLOTS: { who: string; ranking: Option[] }[] = [
  { who: "AK", ranking: ["dolomites", "lisbon", "naxos"] },
  { who: "BM", ranking: ["dolomites", "naxos", "lisbon"] },
  { who: "CJ", ranking: ["dolomites", "lisbon", "naxos"] },
  { who: "DR", ranking: ["dolomites", "naxos", "lisbon"] },
  { who: "EL", ranking: ["lisbon", "dolomites", "naxos"] },
  { who: "FT", ranking: ["lisbon", "naxos", "dolomites"] },
  { who: "GN", ranking: ["lisbon", "dolomites", "naxos"] },
  { who: "HO", ranking: ["naxos", "lisbon", "dolomites"] },
  { who: "IP", ranking: ["naxos", "lisbon", "dolomites"] },
];

/**
 * Instant-runoff, mirroring the backend `tally()`: a strict majority of live first choices wins,
 * all-equal counts are a tie (no winner), otherwise the fewest is dropped. Last-place ties go to
 * the first entry of `options` (the backend drops the lowest ID, so pass options in ID order).
 */
export function runoff<T extends string>(ballots: T[][], options: T[]) {
  const alive = new Set(options);
  const rounds: { counts: Record<string, number>; eliminated: T | null }[] = [];
  if (ballots.length === 0 || options.length === 0) return { rounds, winner: null };
  for (;;) {
    const counts: Record<string, number> = Object.fromEntries([...alive].map((o) => [o, 0]));
    for (const b of ballots) {
      const pick = b.find((o) => alive.has(o));
      if (pick !== undefined) counts[pick] += 1;
    }
    const live = options.filter((o) => alive.has(o));
    const total = Object.values(counts).reduce((a, n) => a + n, 0);
    const lead = live.reduce((a, o) => (counts[o] > counts[a] ? o : a));
    const winner = alive.size === 1 || counts[lead] * 2 > total ? lead : null;
    const tied = new Set(Object.values(counts)).size === 1;
    const eliminated =
      winner !== null || tied ? null : live.reduce((a, o) => (counts[o] < counts[a] ? o : a));
    rounds.push({ counts, eliminated });
    if (eliminated === null) return { rounds, winner };
    alive.delete(eliminated);
  }
}

const RESULT = runoff(
  BALLOTS.map((b) => b.ranking),
  OPTIONS
);

const [R1, R2] = RESULT.rounds;
const ELIMINATED = new Set(RESULT.rounds.flatMap((r) => (r.eliminated ? [r.eliminated] : [])));
const NEEDED = Math.floor(BALLOTS.length / 2) + 1;
const ROWS = [...OPTIONS].sort((a, b) => R1.counts[b] - R1.counts[a]);
if (RESULT.winner === null || RESULT.rounds.length < 2 || ROWS[0] === RESULT.winner)
  throw new Error("sample ballots must show a round-one leader losing to the winner");
const WINNER = RESULT.winner;
export const BOARD_FACTS = {
  total: BALLOTS.length,
  needed: NEEDED,
  leader: ROWS[0],
  names: NAMES,
  winner: WINNER,
  out: [...ELIMINATED][0],
  r1: R1.counts,
  r2: R2.counts,
};

// [ms, phase]: 1 R1 flips, 2 elimination, 3 chips move, 4 R2 flips, 5 winner boards.
const SEQUENCE: [number, number][] = [
  [300, 1],
  [1200, 2],
  [1700, 3],
  [2300, 4],
  [3000, 5],
];
const FINAL = 5;

const TONES = {
  success: "bg-success text-background",
  danger: "bg-danger text-background",
  neutral: "bg-muted text-muted-foreground",
} as const;

/** Flap-style status cell. Fills carry their own text colour, so it also reads on the yellow row. */
function StatusFlap({ tone, children }: { tone: keyof typeof TONES; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center rounded-sm px-2 font-mono text-xs font-medium tracking-wider whitespace-nowrap",
        TONES[tone]
      )}
    >
      {children}
    </span>
  );
}

const th = "px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase";

export function DeparturesBoard() {
  const [reduced] = useState(prefersReducedMotion);
  const [phase, setPhase] = useState(reduced ? FINAL : 0);
  const [run, setRun] = useState(0);
  const timers = useRef<number[]>([]);
  const runId = useRef(0);

  const { ref: boardRef, capture, cancel } = useFlip<HTMLDivElement>(phase, 700, "chip-id");

  const play = useCallback(() => {
    timers.current.forEach(window.clearTimeout);
    cancel();
    const id = ++runId.current;
    setRun(id);
    setPhase(0);
    timers.current = SEQUENCE.map(([ms, next]) =>
      window.setTimeout(() => {
        if (id !== runId.current) return;
        // FLIP: remember where each chip is before it moves rows.
        if (next === 3) capture();
        setPhase(next);
      }, ms)
    );
  }, [cancel, capture]);

  useEffect(() => {
    if (!reduced) play();
    return () => {
      runId.current += 1;
      timers.current.forEach(window.clearTimeout);
    };
  }, [play, reduced]);

  // Chips sit in their final row except while the sequence is before the Naxos move.
  const homeAt = (p: number, ranking: Option[]) =>
    ranking.find((o) => p < 3 || !ELIMINATED.has(o)) ?? ranking[0];

  // Not-yet-revealed content is faded, never removed, so assistive tech always sees the final state.
  const flap = (on: boolean, node: ReactNode) => (
    <span className={cn("inline-block", !on && "opacity-0", on && !reduced && "animate-flip")}>
      {node}
    </span>
  );

  const cell = "px-3 py-3 max-md:p-0";
  const label =
    "max-md:flex max-md:items-baseline max-md:gap-1.5 max-md:before:text-[0.7rem] max-md:before:opacity-70 max-md:before:content-[attr(data-label)]";

  return (
    <div ref={boardRef} className="overflow-x-auto rounded-sm border bg-surface">
      <table role="table" className="w-full border-collapse text-left max-md:block">
        <caption className="caption-top border-b px-3 py-3 text-left text-sm max-md:block">
          <span className="font-mono font-medium">Sample trip</span>
          <span className="text-muted-foreground">
            {" "}
            · {BALLOTS.length.toString()} friends rank {OPTIONS.length.toString()} destinations;{" "}
            {NEEDED.toString()} of {BALLOTS.length.toString()} votes win
          </span>
        </caption>
        <thead role="rowgroup" className="bg-muted text-muted-foreground max-md:sr-only">
          <tr role="row">
            <th role="columnheader" scope="col" className={th}>
              Destination
            </th>
            <th role="columnheader" scope="col" className={th}>
              Voters
            </th>
            <th role="columnheader" scope="col" className={cn(th, "lg:w-28")}>
              R1
            </th>
            <th role="columnheader" scope="col" className={cn(th, "lg:w-28")}>
              R2
            </th>
            <th role="columnheader" scope="col" className={cn(th, "lg:w-44")}>
              Status
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup" className="max-md:block">
          {ROWS.map((opt) => {
            const won = opt === WINNER;
            const out = ELIMINATED.has(opt);
            const boarded = won && phase >= FINAL;
            const chips = BALLOTS.filter((b) => homeAt(phase, b.ranking) === opt);
            const finalVoters = BALLOTS.filter((b) => homeAt(FINAL, b.ranking) === opt);
            return (
              <tr
                key={opt}
                role="row"
                className={cn(
                  "border-t transition-colors duration-300 max-md:grid max-md:grid-cols-[1fr_auto_auto] max-md:items-center max-md:gap-x-4 max-md:gap-y-2 max-md:p-3",
                  boarded && "bg-accent text-accent-foreground"
                )}
              >
                <th
                  role="rowheader"
                  scope="row"
                  className={cn(cell, "text-left max-md:col-span-3 max-md:row-start-1")}
                >
                  <FlapWord
                    key={run}
                    text={NAMES[opt]}
                    size="board"
                    inverted={boarded}
                    flip={!reduced}
                  />
                </th>
                <td role="cell" className={cn(cell, "max-md:row-start-2")}>
                  <span className="sr-only">
                    {finalVoters.map((b) => b.who).join(", ") || "none"}
                  </span>
                  <ul aria-hidden="true" className="flex h-7 items-center gap-1 md:w-39">
                    {chips.map((b) => (
                      <li
                        key={b.who}
                        data-chip-id={b.who}
                        className={cn(
                          "grid size-6 place-items-center rounded-sm font-mono text-[0.65rem] font-medium md:size-7 md:text-xs",
                          boarded ? "bg-accent-foreground text-accent" : "bg-muted text-foreground"
                        )}
                      >
                        {b.who}
                      </li>
                    ))}
                  </ul>
                </td>
                <td
                  role="cell"
                  data-label="R1"
                  className={cn(cell, label, "font-mono tabular-nums max-md:row-start-2")}
                >
                  {flap(phase >= 1, R1.counts[opt])}
                </td>
                <td
                  role="cell"
                  data-label="R2"
                  className={cn(cell, label, "font-mono tabular-nums max-md:row-start-2")}
                >
                  {flap(phase >= 4, out ? "out" : R2.counts[opt])}
                </td>
                <td
                  role="cell"
                  className={cn(
                    cell,
                    "max-md:col-span-3 max-md:row-start-3 max-md:justify-self-start"
                  )}
                >
                  {flap(
                    out ? phase >= 2 : phase >= FINAL,
                    <StatusFlap tone={out ? "danger" : won ? "success" : "neutral"}>
                      {out ? "ELIMINATED" : won ? "BOARDING" : "RUNNER-UP"}
                    </StatusFlap>
                  )}
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
  );
}
