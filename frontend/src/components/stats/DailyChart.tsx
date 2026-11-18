import type { PlatformStats } from "@/types";

type Day = PlatformStats["activity"][number];

const fmt = (n: number) => n.toLocaleString();
const dayLabel = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString("en", { month: "short", day: "numeric" });

/** 30 daily columns scaled to the peak. Chart is one image; the table disclosure holds the numbers. */
export function DailyChart({
  title,
  days,
  value,
  unit,
}: {
  title: string;
  days: Day[];
  value: (d: Day) => number;
  unit: string;
}) {
  const values = days.map(value);
  const total = values.reduce((a, b) => a + b, 0);
  const peak = Math.max(0, ...values);
  const peakDay = days[values.indexOf(peak)];
  const label =
    total === 0
      ? `No ${unit} in the last 30 days`
      : `${fmt(total)} ${unit} in the last 30 days, peak ${fmt(peak)} on ${dayLabel(peakDay.date)}`;

  return (
    <figure>
      <figcaption className="mb-2 text-sm text-muted-foreground">{title}</figcaption>
      <div
        role="img"
        aria-label={label}
        className="flex h-28 items-end gap-px border-b border-foreground"
      >
        {days.map((d, i) => (
          <div key={d.date} className="flex h-full min-w-0 flex-1 items-end">
            {values[i] > 0 && (
              <div
                className="w-full bg-foreground"
                style={{ height: `${Math.max(2, (values[i] / peak) * 100).toString()}%` }}
              />
            )}
          </div>
        ))}
      </div>
      <div
        aria-hidden="true"
        className="mt-1 flex justify-between font-mono text-xs text-muted-foreground"
      >
        <span>{dayLabel(days[0].date)}</span>
        <span>{dayLabel(days[days.length - 1].date)}</span>
      </div>
      {total === 0 && (
        <p className="mt-2 text-sm text-muted-foreground">Nothing in the last 30 days.</p>
      )}
      <details className="mt-2">
        <summary className="inline-flex min-h-11 cursor-pointer items-center text-sm underline underline-offset-4">
          Show as table
        </summary>
        <table className="mt-1 w-full border-collapse text-left text-sm">
          <caption className="sr-only">{title}</caption>
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th
                scope="col"
                className="px-3 py-2 font-mono text-xs font-medium tracking-wider uppercase"
              >
                Date
              </th>
              <th
                scope="col"
                className="px-3 py-2 text-right font-mono text-xs font-medium tracking-wider uppercase"
              >
                {unit}
              </th>
            </tr>
          </thead>
          <tbody>
            {days.map((d, i) => (
              <tr key={d.date} className="border-t">
                <th scope="row" className="px-3 py-1.5 font-normal">
                  {d.date}
                </th>
                <td className="px-3 py-1.5 text-right font-mono tabular-nums">{fmt(values[i])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
