import { useEffect, useId, useRef, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type UniqueIdentifier,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronUp, GripVertical } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/trip";
import { formatBudget, optionTitle } from "@/components/OptionCard";
import type { Itinerary } from "@/types";

interface BallotProps {
  options: Itinerary[];
  /** Receives option ids, best first. Must handle its own errors (toast); a rejection is not caught here. */
  onSubmit: (orderedIds: number[]) => Promise<void>;
  submitLabel: string;
}

interface RowProps {
  option: Itinerary;
  rank: number;
  total: number;
  onMove: (dir: -1 | 1) => void;
}

const iconBtn =
  "inline-flex size-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-30";

function Row({ option, rank, total, onMove }: RowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: option.id });
  const title = optionTitle(option);

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-center gap-1 rounded-xl border bg-surface py-1 pr-1 pl-1",
        isDragging && "relative z-10 shadow-lg ring-1 ring-accent-ink"
      )}
    >
      <button
        type="button"
        ref={setActivatorNodeRef}
        aria-label={`Drag to reorder ${title}`}
        className={cn(iconBtn, "cursor-grab touch-none active:cursor-grabbing")}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-5" aria-hidden="true" />
      </button>
      <span
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold tabular-nums",
          rank === 1 ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground"
        )}
        aria-hidden="true"
      >
        {rank}
      </span>
      <div className="min-w-0 flex-1 px-2">
        <p className="truncate text-sm font-medium">
          <span className="sr-only">{`Rank ${rank.toString()}: `}</span>
          {title}
        </p>
        <p className="truncate text-xs text-muted-foreground tabular-nums">
          {option.daily_itinerary.length} days · {formatBudget(option)}
        </p>
      </div>
      <button
        type="button"
        data-move={`${option.id.toString()}-up`}
        aria-label={`Move ${title} up`}
        disabled={rank === 1}
        onClick={() => {
          onMove(-1);
        }}
        className={iconBtn}
      >
        <ChevronUp className="size-5" aria-hidden="true" />
      </button>
      <button
        type="button"
        data-move={`${option.id.toString()}-down`}
        aria-label={`Move ${title} down`}
        disabled={rank === total}
        onClick={() => {
          onMove(1);
        }}
        className={iconBtn}
      >
        <ChevronDown className="size-5" aria-hidden="true" />
      </button>
    </li>
  );
}

export function Ballot({ options, onSubmit, submitLabel }: BallotProps) {
  const optionKey = options.map((o) => o.id).join(",");
  const [order, setOrder] = useState({ key: optionKey, ids: options.map((o) => o.id) });
  const [pending, setPending] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const list = useRef<HTMLOListElement>(null);
  const refocus = useRef<{ id: number; dir: -1 | 1 } | null>(null);
  const dndId = useId();

  // New option set (e.g. next iteration) -> start from the new options, not the stale order.
  if (order.key !== optionKey) setOrder({ key: optionKey, ids: options.map((o) => o.id) });

  const byId = new Map(options.map((o) => [o.id, o]));
  const ids = order.ids;

  useEffect(() => {
    const target = refocus.current;
    if (!target) return;
    refocus.current = null;
    const [same, other] = target.dir === -1 ? ["up", "down"] : ["down", "up"];
    const find = (d: string) =>
      list.current?.querySelector<HTMLButtonElement>(`[data-move="${target.id.toString()}-${d}"]`);
    // At the end of the list the same-direction button is disabled; keep focus on the other one.
    const btn = find(same);
    (btn && !btn.disabled ? btn : find(other))?.focus();
  }, [order]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const apply = (next: number[], movedId: number) => {
    setOrder({ key: optionKey, ids: next });
    const title = optionTitle(byId.get(movedId) as Itinerary);
    setAnnouncement(
      `${title} moved to position ${(next.indexOf(movedId) + 1).toString()} of ${next.length.toString()}`
    );
  };

  const move = (id: number, dir: -1 | 1) => {
    const from = ids.indexOf(id);
    const to = from + dir;
    if (to < 0 || to >= ids.length) return;
    refocus.current = { id, dir };
    apply(arrayMove(ids, from, to), id);
  };

  // dnd-kit's default live region speaks raw ids; speak option titles and ranks instead.
  const name = (id: UniqueIdentifier) => optionTitle(byId.get(Number(id)) as Itinerary);
  const rankOf = (id: UniqueIdentifier) => `position ${(ids.indexOf(Number(id)) + 1).toString()}`;
  const announcements: Announcements = {
    onDragStart: ({ active }) => `Picked up ${name(active.id)}, currently ${rankOf(active.id)}.`,
    onDragOver: ({ active, over }) =>
      over ? `${name(active.id)} is over ${rankOf(over.id)}.` : undefined,
    onDragEnd: ({ active, over }) =>
      over
        ? `${name(active.id)} dropped at ${rankOf(over.id)}.`
        : `${name(active.id)} dropped, order unchanged.`,
    onDragCancel: ({ active }) => `Cancelled. ${name(active.id)} stays at ${rankOf(active.id)}.`,
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    setOrder({
      key: optionKey,
      ids: arrayMove(ids, ids.indexOf(Number(active.id)), ids.indexOf(Number(over.id))),
    });
  };

  const submit = async () => {
    setPending(true);
    try {
      await onSubmit(ids);
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Rank the options: #1 is your top choice. Drag the handle, or use the arrows.
      </p>
      <DndContext
        id={dndId}
        sensors={sensors}
        collisionDetection={closestCenter}
        accessibility={{ announcements }}
        onDragEnd={onDragEnd}
      >
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          <ol ref={list} className="flex flex-col gap-2">
            {ids.map((id, i) => (
              <Row
                key={id}
                option={byId.get(id) as Itinerary}
                rank={i + 1}
                total={ids.length}
                onMove={(dir) => {
                  move(id, dir);
                }}
              />
            ))}
          </ol>
        </SortableContext>
      </DndContext>
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      <Button
        loading={pending}
        onClick={() => {
          void submit();
        }}
      >
        {submitLabel}
      </Button>
    </div>
  );
}
