import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { TripStatus } from "@/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// ---------------------------------------------------------------------------
// Status meta — single source for organizer and participant views
// ---------------------------------------------------------------------------

export type Tone = "muted" | "flap" | "success" | "warning" | "danger";

export const STATUS: Record<TripStatus, { label: string; tone: Tone }> = {
  CREATED: { label: "Created", tone: "muted" },
  COLLECTING_PREFERENCES: { label: "Collecting", tone: "muted" },
  GENERATING: { label: "Generating", tone: "warning" },
  GENERATION_FAILED: { label: "Failed", tone: "danger" },
  VOTING: { label: "Voting", tone: "flap" },
  FINALIZED: { label: "Finalized", tone: "success" },
};

/** False when matchMedia is missing (jsdom). */
export function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Part before the first comma (whole string if that part is empty), trimmed, capped at `max`. */
export function flapText(s: string, max = 12): string {
  const head = s.split(",")[0].trim();
  return (head || s).trim().slice(0, max).trimEnd();
}

export type TripStage = { index: 0 | 1 | 2 | 3; failed: boolean };

/** Lifecycle position for the gate strip. */
export function tripStage(status: TripStatus): TripStage {
  switch (status) {
    case "CREATED":
    case "COLLECTING_PREFERENCES":
      return { index: 0, failed: false };
    case "GENERATING":
      return { index: 1, failed: false };
    case "GENERATION_FAILED":
      return { index: 1, failed: true };
    case "VOTING":
      return { index: 2, failed: false };
    case "FINALIZED":
      return { index: 3, failed: false };
  }
}

// ---------------------------------------------------------------------------
// Limits — mirror backend clamps; keep in sync with backend schemas/services
// ---------------------------------------------------------------------------

export const TITLE_MAX = 120;
export const DESTINATION_MAX = 100;
export const NOTES_MAX = 2000;
export const NAME_MAX = 80;
export const INTERESTS_MAX = 1000;
export const ACTIVITY_TAG_MAX = 40;
export const ACTIVITY_TAGS_MAX_ITEMS = 20;
export const PARTICIPANT_EMAILS_MAX = 20;
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 72;

const SAFE_OUTPUT_TOKENS = 15_000;
const OPTION_OVERHEAD_TOKENS = 250;
const PER_DAY_TOKENS = 360;

export function maxTripDays(numOptions: number): number {
  if (numOptions < 1) return 1;
  const result = Math.floor(
    (SAFE_OUTPUT_TOKENS - numOptions * OPTION_OVERHEAD_TOKENS) / (numOptions * PER_DAY_TOKENS)
  );
  return Math.max(1, result);
}

// ---------------------------------------------------------------------------
// Dates — ISO "yyyy-MM-dd" strings are calendar dates, parsed in local time
// (new Date("2025-06-01") would be UTC midnight and show the previous day west of UTC).
// ---------------------------------------------------------------------------

const MS_PER_DAY = 86_400_000;

export function parseDate(iso: string): Date {
  // slice: the organizer API sends datetimes ("2025-06-01T00:00:00"), participant API plain dates.
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toISODate(date: Date): string {
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${date.getFullYear().toString()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function todayISO(): string {
  return toISODate(new Date());
}

const dateFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
});

/** "Jun 1, 2025" */
export function formatDate(iso: string): string {
  return dateFormat.format(parseDate(iso));
}

/** "Jun 1" */
export function formatShortDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    parseDate(iso)
  );
}

/** "Jun 1, 2025 – Jun 8, 2025" | "From Jun 1, 2025" | "Until Jun 8, 2025" | null */
export function formatDateRange(start: string | null, end: string | null): string | null {
  if (start && end) return `${formatDate(start)} – ${formatDate(end)}`;
  if (start) return `From ${formatDate(start)}`;
  if (end) return `Until ${formatDate(end)}`;
  return null;
}

/** Whole days from start to end (end - start), by calendar date. */
export function daysBetween(startISO: string, endISO: string): number {
  return Math.round((parseDate(endISO).getTime() - parseDate(startISO).getTime()) / MS_PER_DAY);
}
