import { useEffect, useState, type ReactNode } from "react";
import { cn, prefersReducedMotion, type Tone } from "@/lib/trip";

const FLAP_TONES: Record<Tone, string> = {
  muted: "bg-muted text-muted-foreground",
  flap: "bg-flap text-flap-ink ring-1 ring-flap-edge ring-inset",
  success: "bg-success text-background",
  warning: "bg-warning text-background",
  danger: "bg-danger text-background",
};

/** Solid status flap. Callers remount via `key` to replay `flip`. */
export function StatusFlap({
  tone,
  flip,
  children,
}: {
  tone: Tone;
  flip?: boolean;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center rounded-sm px-2 font-mono text-xs font-medium tracking-wider whitespace-nowrap uppercase",
        FLAP_TONES[tone],
        flip && !prefersReducedMotion() && "animate-flip"
      )}
    >
      {children}
    </span>
  );
}

const TILE_BASE =
  "relative grid h-7 w-5 place-items-center rounded-sm transition-colors duration-300 before:absolute before:inset-x-0 before:top-1/2 before:h-px before:bg-black/60";
const TILE_BOARD = `${TILE_BASE} md:h-9 md:w-6 lg:h-11 lg:w-8`;

/** Freezes its animate flag at mount, so only tiles that appear later flip. */
function Tile({
  ch,
  i,
  board,
  inverted,
  animate,
}: {
  ch: string;
  i: number;
  board: boolean;
  inverted?: boolean;
  animate: boolean;
}) {
  const [flips] = useState(animate);
  return (
    <span
      style={{ animationDelay: `${(i * 45).toString()}ms` }}
      className={cn(
        board ? TILE_BOARD : TILE_BASE,
        inverted
          ? "bg-accent-foreground text-accent"
          : "bg-flap text-flap-ink ring-1 ring-flap-edge ring-inset",
        flips && "animate-flip"
      )}
    >
      {ch}
    </span>
  );
}

/**
 * One split-flap tile per character. First paint never animates: only tiles mounted after the
 * first commit flip (changed characters), unless `flip` forces it.
 */
export function FlapWord({
  text,
  label,
  size,
  inverted,
  flip,
  className,
}: {
  text: string;
  /** sr-only text; defaults to `text`, null renders none (decorative). */
  label?: string | null;
  size: "sm" | "board";
  inverted?: boolean;
  flip?: boolean;
  className?: string;
}) {
  const [late, setLate] = useState(false);
  useEffect(() => {
    setLate(true);
  }, []);
  const animate = flip === true || (late && !prefersReducedMotion());
  const board = size === "board";
  return (
    <>
      {label !== null && <span className="sr-only">{label ?? text}</span>}
      <span
        aria-hidden="true"
        className={cn(
          "flex gap-0.5 font-mono text-sm font-medium uppercase",
          board && "md:text-base lg:text-xl",
          className
        )}
      >
        {text.split("").map((ch, i) => (
          <Tile
            key={`${i.toString()}:${ch}`}
            ch={ch}
            i={i}
            board={board}
            inverted={inverted}
            animate={animate}
          />
        ))}
      </span>
    </>
  );
}
