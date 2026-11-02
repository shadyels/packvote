import { Link } from "react-router-dom";
import { FlapWord, StatusFlap } from "@/components/ui/Flap";
import { Skeleton } from "@/components/ui/Skeleton";
import { STATUS, cn } from "@/lib/trip";
import type { TripSummary } from "@/types";

const th = "px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase";
const cell = "px-3 py-3 max-md:p-0";
const frame = "overflow-hidden rounded-sm border bg-surface";

/** Trips as a departures board: header band, one row per trip, stacked below `md`. */
export function DeparturesList<T extends TripSummary>({
  label,
  trips,
  to,
  linkState,
  loading,
}: {
  /** Table name for assistive tech, e.g. "Created trips". */
  label: string;
  trips: T[];
  to: (trip: T) => string;
  linkState?: unknown;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div role="status" aria-label="Loading trips" className={frame}>
        <div
          aria-hidden="true"
          className={cn(
            th,
            "grid grid-cols-[1fr_8rem_5rem_9rem] bg-muted text-muted-foreground max-md:hidden"
          )}
        >
          <span>Trip</span>
          <span>Code</span>
          <span className="text-right">Prefs</span>
          <span className="pl-6">Status</span>
        </div>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20 rounded-none border-t md:h-16" />
        ))}
      </div>
    );
  }

  return (
    <div className={frame}>
      <table
        role="table"
        aria-label={label}
        className="w-full border-collapse text-left max-md:block md:table-fixed"
      >
        <thead role="rowgroup" className="bg-muted text-muted-foreground max-md:sr-only">
          <tr role="row">
            <th role="columnheader" scope="col" className={th}>
              Trip
            </th>
            <th role="columnheader" scope="col" className={cn(th, "md:w-52")}>
              Code
            </th>
            <th role="columnheader" scope="col" className={cn(th, "text-right md:w-24")}>
              Prefs
            </th>
            <th role="columnheader" scope="col" className={cn(th, "md:w-40")}>
              Status
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup" className="max-md:block">
          {trips.map((t) => {
            const status = STATUS[t.status];
            return (
              <tr
                key={t.id}
                role="row"
                className="relative border-t transition-colors hover:bg-muted has-[a:focus-visible]:bg-muted has-[a:focus-visible]:outline-2 has-[a:focus-visible]:-outline-offset-2 has-[a:focus-visible]:outline-accent-ink max-md:grid max-md:grid-cols-[minmax(0,1fr)_auto] max-md:items-center max-md:gap-x-4 max-md:gap-y-2 max-md:p-3"
              >
                <td role="cell" className={cn(cell, "min-w-0 max-md:row-start-1")}>
                  <Link
                    to={to(t)}
                    state={linkState}
                    className="block min-w-0 after:absolute after:inset-0 after:z-10 focus-visible:outline-none"
                  >
                    <span className="block truncate text-sm font-semibold">{t.title}</span>
                    <span className="block truncate text-sm text-muted-foreground">
                      {t.destination || "Surprise me"}
                    </span>
                  </Link>
                </td>
                <td role="cell" className={cn(cell, "max-md:row-start-2")}>
                  <FlapWord text={t.trip_code} size="sm" />
                </td>
                <td
                  role="cell"
                  className={cn(
                    cell,
                    "text-right font-mono text-sm tabular-nums max-md:col-start-2 max-md:row-start-1"
                  )}
                >
                  {t.preferences_submitted_count}/{t.participant_count}
                </td>
                <td role="cell" className={cn(cell, "max-md:col-start-2 max-md:row-start-2")}>
                  <StatusFlap tone={status.tone}>{status.label}</StatusFlap>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
