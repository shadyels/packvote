import { useState, type ReactNode } from "react";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import { FlapWord, StatusFlap } from "@/components/ui/Flap";
import { STATUS, cn, flapText, tripStage } from "@/lib/trip";
import type { TripStatus } from "@/types";

const STEPS = ["Collecting", "Generating", "Voting", "Finalized"] as const;

function GateStrip({ status }: { status: TripStatus }) {
  const { index, failed } = tripStage(status);
  // Flip the current flap only when the status changes after mount.
  const [seen, setSeen] = useState(status);
  const [changed, setChanged] = useState(false);
  if (seen !== status) {
    setSeen(status);
    setChanged(true);
  }

  return (
    <ol aria-label="Trip progress" className="mt-4 flex gap-1">
      {STEPS.map((label, i) => {
        const current = i === index;
        const done = i < index;
        return (
          <li
            key={label}
            aria-current={current ? "step" : undefined}
            className={cn(
              "min-w-0 flex-1 pt-2",
              done && "border-t-2 border-foreground",
              !done && !current && "border-t border-border text-muted-foreground",
              current && "flex-none border-t-2 sm:flex-1",
              current && (failed ? "border-danger" : "border-foreground")
            )}
          >
            {current ? (
              <StatusFlap key={status} tone={STATUS[status].tone} flip={changed}>
                {STATUS[status].label}
              </StatusFlap>
            ) : (
              <span className="font-mono text-xs tracking-wider uppercase max-sm:sr-only">
                {label}
              </span>
            )}
            {!current && <span className="sr-only">{done ? " (done)" : " (upcoming)"}</span>}
          </li>
        );
      })}
    </ol>
  );
}

type TripHeaderProps = { title: string; status: TripStatus; subline?: ReactNode } & (
  | { code: string; destination?: never }
  | { destination: string | null; code?: never }
);

export function TripHeader(props: TripHeaderProps) {
  const { title, status, subline } = props;

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Trip code copied.");
    } catch {
      toast.error("Could not copy the code.");
    }
  };

  return (
    <header>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight break-words sm:text-3xl">{title}</h1>
          {subline && (
            <div className="mt-1 flex flex-wrap gap-x-3 text-sm text-muted-foreground">
              {subline}
            </div>
          )}
        </div>
        {props.code !== undefined ? (
          <button
            type="button"
            aria-label={`Copy trip code ${props.code}`}
            onClick={() => {
              void copyCode(props.code);
            }}
            className="inline-flex min-h-11 shrink-0 items-center gap-2 self-start text-muted-foreground hover:text-foreground sm:self-auto"
          >
            <FlapWord text={props.code} label={null} size="board" />
            <Copy className="size-3.5" aria-hidden="true" />
          </button>
        ) : props.destination ? (
          <FlapWord text={flapText(props.destination)} label={props.destination} size="board" />
        ) : (
          <p className="text-muted-foreground">Destination TBD</p>
        )}
      </div>
      <GateStrip status={status} />
    </header>
  );
}
