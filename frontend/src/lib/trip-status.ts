import type { TripStatus } from "@/types";

export const STATUS_CONFIG: Record<
  TripStatus,
  { label: string; className: string }
> = {
  CREATED: {
    label: "Created",
    className: "bg-zinc-100 text-zinc-700 hover:bg-zinc-100",
  },
  COLLECTING_PREFERENCES: {
    label: "Collecting",
    className: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  },
  GENERATING: {
    label: "Generating",
    className: "bg-amber-100 text-amber-700 hover:bg-amber-100",
  },
  GENERATION_FAILED: {
    label: "Failed",
    className: "bg-red-100 text-red-700 hover:bg-red-100",
  },
  VOTING: {
    label: "Voting",
    className: "bg-brand/20 text-brand hover:bg-brand/20",
  },
  ITERATING: {
    label: "Iterating",
    className: "bg-purple-100 text-purple-700 hover:bg-purple-100",
  },
  FINALIZED: {
    label: "Finalized",
    className: "bg-green-100 text-green-700 hover:bg-green-100",
  },
};
