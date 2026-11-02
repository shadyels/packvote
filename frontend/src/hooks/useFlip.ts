import { useCallback, useEffect, useLayoutEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/trip";

/**
 * FLIP for children marked `data-${attr}="<id>"` under `ref`: call `capture()` right before a
 * state change moves them; when `dep` changes they slide from their old position (before paint).
 * `capture()` must be followed by a change to `dep` in the same update, or the stale
 * viewport-relative rects would animate a later, unrelated change.
 * No timers. Skipped under reduced motion (WAAPI ignores the global CSS rule) or without WAAPI.
 */
export function useFlip<T extends HTMLElement>(dep: unknown, duration: number, attr = "flip-id") {
  const ref = useRef<T>(null);
  const rects = useRef(new Map<string, DOMRect>());
  const anims = useRef<Animation[]>([]);
  const dataAttr = `data-${attr}`;

  const capture = useCallback(() => {
    if (prefersReducedMotion() || !ref.current) return;
    ref.current.querySelectorAll<HTMLElement>(`[${dataAttr}]`).forEach((el) => {
      rects.current.set(el.getAttribute(dataAttr) ?? "", el.getBoundingClientRect());
    });
  }, [dataAttr]);

  const cancel = useCallback(() => {
    anims.current.forEach((a) => {
      a.cancel();
    });
    anims.current = [];
    rects.current.clear();
  }, []);

  useLayoutEffect(() => {
    if (rects.current.size === 0 || !ref.current) return;
    // In-flight transforms would skew the measurement below; drop them and finished handles.
    anims.current.forEach((a) => {
      a.cancel();
    });
    anims.current = [];
    ref.current.querySelectorAll<HTMLElement>(`[${dataAttr}]`).forEach((el) => {
      const from = rects.current.get(el.getAttribute(dataAttr) ?? "");
      if (!from || typeof el.animate !== "function") return;
      const to = el.getBoundingClientRect();
      const dx = from.left - to.left;
      const dy = from.top - to.top;
      if (dx === 0 && dy === 0) return;
      anims.current.push(
        el.animate(
          [
            { transform: `translate(${dx.toString()}px, ${dy.toString()}px)` },
            { transform: "none" },
          ],
          { duration, easing: "cubic-bezier(0.16, 1, 0.3, 1)" }
        )
      );
    });
    rects.current.clear();
  }, [dep, duration, dataAttr]);

  useEffect(() => cancel, [cancel]);

  return { ref, capture, cancel };
}
