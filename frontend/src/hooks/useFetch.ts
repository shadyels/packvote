import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

interface FetchOptions<T> {
  /**
   * Given the latest successful data, returns the delay in ms until the next poll, or `null` to
   * stop. A failed poll retries after the last delay used. While the tab is hidden the request is
   * skipped and the same delay is rescheduled.
   */
  poll?: (data: T) => number | null;
}

interface FetchResult<T> {
  data: T | null;
  error: string | null;
  /** True only until the first successful load (no data yet). */
  isLoading: boolean;
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
  { poll }: FetchOptions<T> = {}
): FetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [tick, setTick] = useState(0);

  // Always call the latest closures without re-running the effect on every render.
  const fetcherRef = useRef(fetcher);
  const pollRef = useRef(poll);
  fetcherRef.current = fetcher;
  pollRef.current = poll;

  const requestId = useRef(0);
  const hasData = useRef(false);
  const lastDelay = useRef<number | null>(null);

  const refetch = useCallback(() => {
    // Invalidate in-flight responses now; the effect only bumps the id after commit.
    requestId.current++;
    setTick((t) => t + 1);
  }, []);

  const lastDeps = useRef<DependencyList | null>(null);

  useEffect(() => {
    // New deps mean a different resource: forget old data and show the loading state again.
    const prev = lastDeps.current;
    if (!prev || prev.length !== deps.length || prev.some((d, i) => !Object.is(d, deps[i]))) {
      hasData.current = false;
      lastDelay.current = null;
    }
    lastDeps.current = deps;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const id = ++requestId.current;

    const schedule = (delay: number) => {
      timer = setTimeout(() => {
        if (document.hidden) schedule(delay);
        else run();
      }, delay);
    };

    const run = () => {
      if (!hasData.current) {
        setIsLoading(true);
        setData(null);
        setError(null);
      }
      fetcherRef
        .current()
        .then((result) => {
          if (!active || id !== requestId.current) return;
          hasData.current = true;
          setData(result);
          setError(null);
          setIsLoading(false);
          lastDelay.current = pollRef.current?.(result) ?? null;
          if (lastDelay.current !== null) schedule(lastDelay.current);
        })
        .catch((err: unknown) => {
          if (!active || id !== requestId.current) return;
          setError(err instanceof Error ? err.message : "Something went wrong");
          setIsLoading(false);
          // A failed poll keeps the last data and tries again after the last delay.
          if (hasData.current && lastDelay.current !== null) schedule(lastDelay.current);
        });
    };
    run();

    return () => {
      active = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller-provided deps
  }, [...deps, tick]);

  return { data, error, isLoading, refetch };
}
