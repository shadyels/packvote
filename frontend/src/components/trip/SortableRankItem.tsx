import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import type { Itinerary } from "@/types";
import { parseJson } from "@/lib/utils";

interface SortableRankItemProps {
  itinerary: Itinerary;
  rank: number;
  isDragging?: boolean;
}

function formatBudget(amount: number, currency: string): string {
  if (amount >= 1_000_000) {
    return `${currency} ${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `${currency} ${(amount / 1_000).toFixed(0)}K`;
  }
  return `${currency} ${amount.toLocaleString()}`;
}

export function SortableRankItem({
  itinerary,
  rank,
  isDragging = false,
}: SortableRankItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: itinerary.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Parse day count from daily_itinerary_json
  const days = parseJson<unknown[]>(itinerary.daily_itinerary_json, []).length;

  // Parse highlight count
  const highlights = parseJson<string[]>(itinerary.highlights, []).length;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={[
        "flex items-center gap-3 rounded-lg border bg-card px-4 py-3 select-none cursor-grab active:cursor-grabbing touch-none",
        isDragging
          ? "shadow-lg border-brand/40 ring-1 ring-brand/20 scale-[1.02] z-50 opacity-90"
          : "border-border shadow-sm hover:shadow-md transition-shadow duration-150",
      ].join(" ")}
      {...attributes}
      {...listeners}
    >
      {/* Rank badge */}
      <div
        className={[
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold",
          rank === 1
            ? "bg-brand text-white"
            : "bg-muted text-muted-foreground",
        ].join(" ")}
      >
        {rank}
      </div>

      {/* Drag handle affordance */}
      <div className="shrink-0 p-1 text-muted-foreground">
        <GripVertical className="h-4 w-4" />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {itinerary.option_title ?? itinerary.destination_name}
        </p>
        <p className="text-xs text-muted-foreground truncate">
          {[
            itinerary.option_title && itinerary.destination_name,
            highlights > 0 && `${highlights.toString()} highlight${highlights !== 1 ? "s" : ""}`,
            days > 0 && `${days.toString()} day${days !== 1 ? "s" : ""}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>

      {/* Budget */}
      <p className="shrink-0 text-sm font-semibold text-brand">
        {formatBudget(itinerary.total_estimated_budget, itinerary.currency)}
      </p>
    </div>
  );
}
