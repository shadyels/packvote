import type { ReactNode } from "react";

interface BarRow {
  key: string;
  label: ReactNode;
  value: number;
}

/** Horizontal bars as a real table: the number is always text, the bar is decoration. */
export function BarTable({
  caption,
  labelHeader,
  valueHeader,
  rows,
  empty,
}: {
  caption: string;
  labelHeader: string;
  valueHeader: string;
  rows: BarRow[];
  empty: string;
}) {
  const max = Math.max(0, ...rows.map((r) => r.value));
  const th = "px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase";
  const cell = "px-3 py-2 max-md:p-0";
  return (
    <table role="table" className="w-full border-collapse text-left max-md:block">
      <caption className="mb-2 text-left text-sm text-muted-foreground max-md:block">
        {caption}
      </caption>
      {rows.length === 0 ? (
        <tbody>
          <tr>
            <td className="border-t py-3 text-sm text-muted-foreground">{empty}</td>
          </tr>
        </tbody>
      ) : (
        <>
          <thead role="rowgroup" className="bg-muted text-muted-foreground max-md:sr-only">
            <tr role="row">
              <th role="columnheader" scope="col" className={th}>
                {labelHeader}
              </th>
              <th role="columnheader" scope="col" className={th}>
                Share of largest
              </th>
              <th role="columnheader" scope="col" className={`${th} text-right`}>
                {valueHeader}
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup" className="max-md:block">
            {rows.map((r) => (
              <tr
                key={r.key}
                role="row"
                className="border-t max-md:grid max-md:grid-cols-[1fr_auto] max-md:items-baseline max-md:gap-x-4 max-md:gap-y-1.5 max-md:px-0 max-md:py-2.5"
              >
                <th
                  role="rowheader"
                  scope="row"
                  className={`${cell} text-sm font-normal max-md:row-start-1 md:w-2/5`}
                >
                  {r.label}
                </th>
                <td role="cell" className={`${cell} max-md:col-span-2 max-md:row-start-2`}>
                  <div aria-hidden="true" className="h-2 rounded-sm bg-muted">
                    <div
                      className="h-full rounded-sm bg-foreground"
                      style={{ width: `${max > 0 ? ((r.value / max) * 100).toString() : "0"}%` }}
                    />
                  </div>
                </td>
                <td
                  role="cell"
                  className={`${cell} text-right font-mono text-sm tabular-nums max-md:col-start-2 max-md:row-start-1 md:w-24`}
                >
                  {r.value.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </>
      )}
    </table>
  );
}
